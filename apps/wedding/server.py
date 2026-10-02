"""WSGI application. Gunicorn serves production; SQLite owns all shared state."""
from contextlib import contextmanager
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import unicodedata
from urllib.parse import parse_qs, urlsplit
from engine import TRAIN_HINTS, SNAKE_HINTS, initial, advance, command, view, GameError
from game import previous_pin_game, gallery_key

PUBLIC = Path(__file__).parent / 'public'


def normalize(value):
    return ''.join(unicodedata.normalize('NFKC', value).upper().split())


class App:
    def __init__(self, config_path, db_path):
        self.config = json.loads(Path(config_path).read_text())
        self.game = self.config['game']
        self.lab_key = gallery_key(self.config)
        if self.game.get('schema') != 2:
            raise ValueError('CUP v2 benötigt eine neu eingerichtete Konfiguration und einen eigenen Spielstand.')
        self.origin = os.getenv('WEDDING_ORIGIN') or self.config['origin']
        self.origins = set((os.getenv('WEDDING_ORIGINS') or self.origin).split())
        for origin in self.origins:
            parsed = urlsplit(origin)
            if not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise ValueError('Origin muss eine vollständige Adresse ohne Pfad sein.')
            if parsed.scheme != 'https' and not (os.getenv('WEDDING_ALLOW_HTTP') == '1' and parsed.scheme == 'http' and parsed.hostname == '127.0.0.1'):
                raise ValueError('HTTPS ist erforderlich.')
        self.secure = all(origin.startswith('https://') for origin in self.origins)
        self.db_path = str(db_path)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS progress (id INTEGER PRIMARY KEY CHECK(id=1), stage INTEGER NOT NULL, a INTEGER NOT NULL, b INTEGER NOT NULL, version INTEGER NOT NULL);
                INSERT OR IGNORE INTO progress VALUES (1,0,0,0,0);
                CREATE TABLE IF NOT EXISTS hints (stage INTEGER, role TEXT, count INTEGER, PRIMARY KEY(stage,role));
                CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, role TEXT, csrf TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, start REAL, count INTEGER);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS runtime (id INTEGER PRIMARY KEY CHECK(id=1), stage INTEGER, payload TEXT);
                CREATE TABLE IF NOT EXISTS awards (key TEXT PRIMARY KEY, value TEXT);
            ''')
            fingerprint = hashlib.sha256(json.dumps(self.game, sort_keys=True).encode()).hexdigest()
            existing = db.execute("SELECT value FROM metadata WHERE key='game'").fetchone()
            if existing and existing[0] != fingerprint:
                previous = previous_pin_game(self.game)
                old_fingerprint = hashlib.sha256(json.dumps(previous, sort_keys=True).encode()).hexdigest()
                if existing[0] != old_fingerprint:
                    raise ValueError('Spielinhalt geändert. Für eine neue Version eine neue Datenbank verwenden; Fortschritt nicht überschreiben.')
                db.execute("UPDATE metadata SET value=? WHERE key='game'", (fingerprint,))
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('game',?)", (fingerprint,))
        os.chmod(self.db_path, 0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def limited(self, key, maximum, seconds):
        now = time.time()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT start,count FROM limits WHERE key=?', (key,)).fetchone()
            count = row['count'] + 1 if row and now-row['start'] < seconds else 1
            start = row['start'] if row and now-row['start'] < seconds else now
            db.execute('INSERT OR REPLACE INTO limits VALUES (?,?,?)', (key,start,count))
        return count > maximum

    def session(self, env, role):
        try:
            cookies = SimpleCookie(env.get('HTTP_COOKIE',''))
            token = cookies[f'wedding_{role}'].value
        except (KeyError, ValueError):
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.db() as db:
            return db.execute('SELECT * FROM sessions WHERE token=? AND role=? AND expires>?', (digest,role,time.time())).fetchone()

    def load_runtime(self, db, stage):
        row = db.execute('SELECT stage,payload FROM runtime WHERE id=1').fetchone()
        runtime=json.loads(row['payload']) if row and row['stage']==stage else initial(stage)
        if stage==0:
            before=json.dumps(runtime)
            if 'ping' in runtime:
                runtime.pop('ping');runtime['last']='Das Stellwerk stellt die Weiche. Der Fahrer bedient Gas und Bremse.'
            for key,value in [('switch_direction',None),('motion','stopped'),('travel',None)]:runtime.setdefault(key,value)
            if before!=json.dumps(runtime):self.save_runtime(db,stage,runtime)
        return runtime

    def save_runtime(self, db, stage, runtime):
        db.execute('INSERT OR REPLACE INTO runtime VALUES (1,?,?)', (stage,json.dumps(runtime)))
        db.execute('UPDATE progress SET version=version+1 WHERE id=1')

    def state(self, role, session):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            progress=db.execute('SELECT * FROM progress').fetchone()
            stage=progress['stage']
            runtime=self.load_runtime(db,stage)
            before=json.dumps(runtime)
            advance(stage,runtime,time.time(),role)
            if before!=json.dumps(runtime): self.save_runtime(db,stage,runtime)
            progress=db.execute('SELECT * FROM progress').fetchone()
            row=db.execute('SELECT count FROM hints WHERE stage=? AND role=?',(stage,role)).fetchone()
            count=row[0] if row else 0
            award=db.execute("SELECT value FROM awards WHERE key='cup'").fetchone()
            reset_epoch=db.execute("SELECT value FROM metadata WHERE key='reset'").fetchone()
        result=dict(role=role,name=self.game['names'][role],partner=self.game['names']['b' if role=='a' else 'a'],
                    title=self.game['title'],stage=stage,total=len(self.game['stages']),version=progress['version'],
                    reset_epoch=reset_epoch[0] if reset_epoch else 'initial',
                    solved=bool(progress[role]),peer_solved=bool(progress['b' if role=='a' else 'a']),csrf=session['csrf'],
                    rewards=[s['reward'] for s in self.game['stages'][:stage] if s['reward']],complete=stage==len(self.game['stages']),
                    cup=award['value'] if award else None)
        if result['complete']:
            result.update(code=self.game['code'],greeting=self.game['greeting'])
        else:
            current=self.game['stages'][stage]
            result.update(stage_title=current['title'],subtitle=current['subtitle'],minutes=current['minutes'],
                          intro=(('Du bedienst Gas und Bremse. Dein Gegenüber stellt die Weiche.' if role==('b' if runtime['leg']==0 else 'a') else 'Du stellst die Weiche. Dein Gegenüber bedient Gas und Bremse.') if stage==0 else current['copy'][role]),hints=(TRAIN_HINTS['driver' if role==('b' if runtime['leg']==0 else 'a') else 'signal'] if stage==0 else SNAKE_HINTS if stage==1 else current['hints'][role])[:count],play=view(self.game,stage,runtime,role,time.time()))
        return result

    def __call__(self, env, start_response):
        try:
            return self.handle(env,start_response)
        except (ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError):
            return self.respond(start_response,400,{'error':'Ungültige Anfrage.'})
        except Exception:
            # Never log request URLs, cookies, submitted answers or personal configuration.
            import logging
            logging.getLogger('wedding').error('Interner Fehler bei der Anfrageverarbeitung.')
            return self.respond(start_response,500,{'error':'Bitte versuche es gleich noch einmal.'})

    def respond(self, start, status, body, mime='application/json; charset=utf-8', extra=()):
        if mime.startswith('application/json'):
            body = json.dumps(body,ensure_ascii=False).encode()
        elif isinstance(body,str):
            body = body.encode()
        names={200:'OK',303:'See Other',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',405:'Method Not Allowed',409:'Conflict',413:'Content Too Large',429:'Too Many Requests',500:'Internal Server Error'}
        headers=[('Content-Type',mime),('Content-Length',str(len(body))), *self.headers(), *extra]
        start(f'{status} {names[status]}',headers)
        return [body]

    def headers(self):
        return [('Cache-Control','no-store'),('Referrer-Policy','strict-origin'),('X-Content-Type-Options','nosniff'),
                ('X-Frame-Options','DENY'),('X-Robots-Tag','noindex, nofollow, noarchive'),
                ('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
                ('Permissions-Policy','camera=(), microphone=(), geolocation=()')]

    def handle(self, env, start):
        path, method = env.get('PATH_INFO','/'), env['REQUEST_METHOD']
        def reply(status,body,**kwargs):
            return self.respond(start,status,body,**kwargs)
        if method not in ('GET','POST'):
            return reply(405,{'error':'Methode nicht erlaubt.'})
        if path == '/healthz' and method=='GET':
            with self.db() as db:
                db.execute('SELECT 1 FROM progress').fetchone()
            return reply(200,{'status':'ok'})
        if path == '/robots.txt' and method=='GET':
            return reply(200,'User-agent: *\nDisallow: /lab/\n\n# Manche Verzeichnisse sind für neugierige Menschen gedacht.\n',mime='text/plain; charset=utf-8')
        if path.startswith('/lab/') and method=='GET':
            if not self.session(env,'b'):
                return reply(404,{'error':'Nicht gefunden.'})
            if path == '/lab/':
                return reply(200,(PUBLIC/'lab.html').read_bytes(),mime='text/html; charset=utf-8',
                             extra=[('X-CUP-Next','/lab/manifest.json')])
            if path == '/lab/manifest.json':
                return reply(200,{'format':'CUP-Lab/1','artifact':'L2xhYi9nYWxsZXJ5',
                                  'hint':'Das Artefakt ist Base64-kodiert. Dekodiere es als UTF-8-Pfad.',
                                  'decryptor':'/lab/decryptor.js','bundle':'/lab/gallery.cup',
                                  'cipher':'CUPX2 · AES-CTR-Keystream XOR + HMAC-SHA-256',
                                  'key_hex':self.lab_key.hex()})
            if path == '/lab/gallery':
                return reply(200,(PUBLIC/'lab-gallery.html').read_bytes(),mime='text/html; charset=utf-8')
            if path == '/lab/decryptor.js':
                return reply(200,(PUBLIC/'lab-decryptor.js').read_bytes(),mime='text/javascript; charset=utf-8')
            if path == '/lab/gallery.cup':
                return reply(200,(PUBLIC/'study-gallery.cup').read_bytes(),mime='application/octet-stream')
            return reply(404,{'error':'Nicht gefunden.'})
        # Only neutral login styling is public; every game asset requires a role session.
        if path == '/login.js' and method=='GET':
            return reply(200,(PUBLIC/'login.js').read_bytes(),mime='text/javascript; charset=utf-8')
        if path == '/style.css' and method=='GET':
            return reply(200,(PUBLIC/'style.css').read_bytes(),mime='text/css; charset=utf-8')
        if path == '/' and method=='GET':
            return reply(200,(PUBLIC/'login.html').read_text().replace('{{MESSAGE}}','Öffne deinen persönlichen Einladungslink, um zu beginnen.').replace('{{FORM}}',''),mime='text/html; charset=utf-8')
        if path in ('/app.js','/arcade.js','/vendor/phaser.min.js') and method=='GET':
            if not any(self.session(env,r) for r in ('a','b')):
                return reply(401,{'error':'Bitte melde dich an.'})
            return reply(200,(PUBLIC/path.lstrip('/')).read_bytes(),mime='text/javascript; charset=utf-8')
        pieces=path.strip('/').split('/')
        if pieces[0] in ('a','b') and len(pieces) in (1,2):
            role=pieces[0]
            if len(pieces)==1:
                if not self.session(env,role):
                    return reply(401,(PUBLIC/'login.html').read_text().replace('{{MESSAGE}}','Bitte öffne deinen persönlichen Einladungslink erneut und melde dich an. Dein Fortschritt bleibt erhalten.').replace('{{FORM}}',''),mime='text/html; charset=utf-8')
                if method!='GET':
                    return reply(405,{'error':'Methode nicht erlaubt.'})
                return reply(200,(PUBLIC/'index.html').read_bytes(),mime='text/html; charset=utf-8')
            token=pieces[1]
            valid_role=self.config['roles'].get(hashlib.sha256(token.encode()).hexdigest())
            if valid_role != role:
                return reply(404,{'error':'Einladung nicht gefunden.'})
            if method=='GET' and self.session(env,role):
                return reply(303,'',mime='text/plain',extra=[('Location',f'/{role}')])
            message='Melde dich mit eurem gemeinsamen Passwort an.'
            status=200
            if method=='POST':
                if env.get('HTTP_ORIGIN') not in self.origins:
                    return reply(403,{'error':'Anfrage nicht erlaubt.'})
                if self.limited('login',30,60):
                    return reply(429,{'error':'Zu viele Versuche. Bitte warte eine Minute.'},extra=[('Retry-After','60')])
                length=int(env.get('CONTENT_LENGTH') or 0)
                if length>4096:
                    return reply(413,{'error':'Anfrage zu groß.'})
                form=parse_qs(env['wsgi.input'].read(length).decode())
                password=form.get('password',[''])[0]
                _,salt,expected=self.config['password_hash'].split('$')
                actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
                if hmac.compare_digest(actual,expected):
                    cookie=secrets.token_urlsafe(32)
                    with self.db() as db:
                        db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
                        db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(hashlib.sha256(cookie.encode()).hexdigest(),role,secrets.token_urlsafe(32),time.time()+7*86400))
                    flags='; Secure' if self.secure else ''
                    return reply(303,'',mime='text/plain',extra=[('Location',f'/{role}'),('Set-Cookie',f'wedding_{role}={cookie}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800{flags}')])
                message='Das Passwort stimmt nicht. Bitte versuche es erneut.'
                status=401
            form='<form method="post"><label for="password">Euer Passwort</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="256"><button type="submit">Anmelden</button></form>'
            return reply(status,(PUBLIC/'login.html').read_text().replace('{{MESSAGE}}',message).replace('{{FORM}}',form),mime='text/html; charset=utf-8')
        if len(pieces)!=3 or pieces[0]!='api' or pieces[1] not in ('a','b'):
            return reply(404,{'error':'Nicht gefunden.'})
        _,role,action=pieces
        session=self.session(env,role)
        if not session:
            return reply(401,{'error':'Bitte öffne deinen Einladungslink und melde dich erneut an.'})
        if method=='GET' and action=='state':
            return reply(200,self.state(role,session))
        if method=='GET' and action=='archive':
            with self.db() as db:
                stage=db.execute('SELECT stage FROM progress').fetchone()[0]
                runtime=self.load_runtime(db,stage)
            if role!='b' or stage!=3 or not runtime.get('unlocked'):
                return reply(403,{'error':'Prüft zuerst gemeinsam die Schaltung. Das Archiv gehört zur technischen Seite.'})
            archive=self.game['archive']
            return reply(200,dict(format='CUP-Archiv/1',salt=archive['salt'],cipher_hex=archive['cipher_hex'],
                                  key='SHA-256(UTF-8(Schlüsselteil + ":" + Salz))',
                                  decrypt='XOR: acht Geheimtext-Bytes mit den ersten acht Schlüssel-Bytes. Das Ergebnis sind acht ASCII-Ziffern im Format TTMMJJJJ.',
                                  value='Absoluter Unterschied zwischen Tag und Monat, modulo 10.',
                                  receipt='SHA-256(UTF-8(Salz + ":" + entschlüsselte Ziffern)). Die ersten acht Hexzeichen, großgeschrieben, sind das Prüfwort.'))
        if method=='GET' and action=='events':
            start('200 OK',[('Content-Type','text/event-stream; charset=utf-8'), *self.headers(),('X-Accel-Buffering','no')])
            def events():
                previous=None
                for _ in range(100):
                    if not self.session(env,role):
                        yield b'event: expired\ndata: {}\n\n'
                        return
                    state=self.state(role,session)
                    marker=(state['version'],len(state.get('hints',[])))
                    if marker!=previous:
                        yield ('data: '+json.dumps(state,ensure_ascii=False)+'\n\n').encode()
                        previous=marker
                    else:
                        yield b': verbunden\n\n'
                    time.sleep(.5 if state['stage']==1 else .25)
            return events()
        if method!='POST' or action not in ('action','hint','logout'):
            return reply(404,{'error':'Nicht gefunden.'})
        if env.get('HTTP_ORIGIN') not in self.origins or not hmac.compare_digest(env.get('HTTP_X_CSRF_TOKEN',''),session['csrf']):
            return reply(403,{'error':'Bitte lade die Seite neu.'})
        if action=='logout':
            with self.db() as db:
                db.execute('DELETE FROM sessions WHERE token=?',(session['token'],))
            return reply(200,{'ok':True},extra=[('Set-Cookie',f'wedding_{role}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'+('; Secure' if self.secure else ''))])
        length=int(env.get('CONTENT_LENGTH') or 0)
        if length>4096:
            return reply(413,{'error':'Anfrage zu groß.'})
        data=json.loads(env['wsgi.input'].read(length))
        if not isinstance(data,dict):
            return reply(400,{'error':'Bitte sende eine Spielaktion.'})
        if self.limited('action:'+role,600,60):
            return reply(429,{'error':'Bitte warte kurz, bevor du die nächste Aktion ausführst.'},extra=[('Retry-After','60')])
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            progress=db.execute('SELECT * FROM progress').fetchone()
            stage=progress['stage']
            if data.get('stage')!=stage or stage>=len(self.game['stages']):
                return reply(409,{'error':'Ihr seid bereits in der nächsten Etappe. Der neue Stand wird geladen.'})
            runtime=self.load_runtime(db,stage)
            advance(stage,runtime,time.time(),role)
            if action=='hint':
                db.execute('INSERT INTO hints VALUES (?,?,1) ON CONFLICT(stage,role) DO UPDATE SET count=MIN(count+1,3)',(stage,role))
            else:
                try:
                    solved=command(self.game,stage,runtime,role,data,time.time())
                except GameError as error:
                    return reply(400,{'error':str(error)})
                if data.get('kind') in ('place','rotate'):
                    db.execute('UPDATE progress SET a=0,b=0 WHERE id=1')
                if solved:
                    db.execute(f'UPDATE progress SET {role}=1 WHERE id=1')
            self.save_runtime(db,stage,runtime)
            row=db.execute('SELECT a,b FROM progress').fetchone()
            if row['a'] and row['b']:
                if stage==1:
                    db.execute("INSERT OR REPLACE INTO awards VALUES ('cup',?)",(runtime['winner'],))
                db.execute('UPDATE progress SET stage=stage+1,a=0,b=0,version=version+1 WHERE id=1')

        return reply(200,self.state(role,session))


def create_app():
    os.umask(0o077)
    return App(os.getenv('WEDDING_CONFIG','/run/secrets/wedding/config.json'),os.getenv('WEDDING_DB','/data/game.sqlite3'))
