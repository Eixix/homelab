import concurrent.futures
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game import make_game
from server import App
from setup import password_hash
from engine import initial, advance, command, snake_tick, GameError, RACE_SECONDS, TRAIN_SECONDS, view


class GameTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.config=Path(self.tmp.name)/'config.json'
        self.database=Path(self.tmp.name)/'game.sqlite3'
        self.password='test-only-long-password'
        self.game=make_game(dict(relationship_date='2019-06-13'))
        self.config.write_text(json.dumps(dict(origin='https://wedding.example',password_hash=password_hash(self.password),roles={hashlib.sha256(r.encode()).hexdigest():r for r in ('a','b')},game=self.game)))
        self.app=App(self.config,self.database)
        self.cookies={};self.csrf={}

    def tearDown(self): self.tmp.cleanup()

    def call(self,path,method='GET',body=None,role=None,origin='https://wedding.example',csrf=True,stream=False):
        payload=body.encode() if isinstance(body,str) else json.dumps(body).encode() if body is not None else b''
        env=dict(PATH_INFO=path,REQUEST_METHOD=method,CONTENT_LENGTH=str(len(payload)),HTTP_ORIGIN=origin,**{'wsgi.input':BytesIO(payload)})
        if role:
            env['HTTP_COOKIE']=self.cookies.get(role,'')
            if csrf:env['HTTP_X_CSRF_TOKEN']=self.csrf.get(role,'')
        captured={}
        def start(status,headers):captured.update(status=int(status.split()[0]),headers=dict(headers))
        iterator=self.app(env,start)
        if stream:return captured,iterator
        data=b''.join(iterator)
        if captured['headers']['Content-Type'].startswith('application/json'):data=json.loads(data)
        return captured,data

    def login(self,role,origin='https://wedding.example'):
        meta,_=self.call(f'/{role}/{role}','POST','password='+self.password,origin=origin)
        self.assertEqual(meta['status'],303)
        self.assertIn('Secure',meta['headers']['Set-Cookie']);self.assertIn('HttpOnly',meta['headers']['Set-Cookie'])
        self.assertNotIn('Domain=',meta['headers']['Set-Cookie'])
        self.cookies[role]=meta['headers']['Set-Cookie'].split(';')[0]
        _,state=self.call(f'/api/{role}/state',role=role)
        self.csrf[role]=state['csrf'];return state

    def state(self,role):return self.call(f'/api/{role}/state',role=role)[1]
    def act(self,role,stage,kind,**extra):return self.call(f'/api/{role}/action','POST',dict(stage=stage,kind=kind,**extra),role)

    def train(self,confirm=True):
        with patch('server.time.time') as clock:
            now=1000
            for signal,driver,directions in [('a','b',['down','right','down','right']),('b','a',['up','left','up','left'])]:
                for direction in directions:
                    clock.return_value=now
                    node=self.state(signal)['play']['position']
                    self.assertEqual(self.act(signal,0,'set_switch',node=node,direction=direction)[0]['status'],200)
                    self.assertEqual(self.act(driver,0,'throttle',node=node)[0]['status'],200)
                    self.assertEqual(self.state(driver)['play']['position'],node)
                    now+=TRAIN_SECONDS+.01;clock.return_value=now
                    self.state(signal);self.state(driver)
            self.assertTrue(self.state('a')['play']['done'])
            if confirm:
                self.act('a',0,'confirm');self.assertEqual(self.state('b')['stage'],0)
                self.act('b',0,'confirm');self.assertEqual(self.state('a')['stage'],1)

    def race(self):
        with patch('server.time.time') as clock:
            clock.return_value=5000
            self.act('a',1,'ready');self.act('b',1,'ready')
            for i in range(RACE_SECONDS+5):
                clock.return_value=5000+i
                self.state('a');self.state('b')
            self.assertEqual(self.state('a')['play']['phase'],'passport')
            for i in range(11):
                if self.state('a')['play']['passport'][i]: continue
                self.assertEqual(self.act('a' if i%2==0 else 'b',1,'stamp',station=i)[0]['status'],200)
            self.act('a',1,'confirm');self.act('b',1,'confirm')
        self.assertEqual(self.state('a')['stage'],2)

    def album(self):
        for r in ['a','b']:
            for i in range(4):self.act(r,2,'place',item=i,position=i)
        self.act('a',2,'confirm');self.act('b',2,'confirm')
        self.assertEqual(self.state('a')['stage'],3)

    def circuit(self):
        self.assertEqual(self.act('a',3,'switch',index=2)[0]['status'],400)
        self.act('a',3,'switch',index=0);self.act('b',3,'switch',index=2)
        self.act('a',3,'check');self.assertEqual(self.call('/api/b/archive',role='b')[0]['status'],403)
        self.act('b',3,'check')

    def test_access_origins_csrf_and_role_boundaries(self):
        for path in ['/a','/app.js','/arcade.js','/vendor/phaser.min.js','/api/a/state','/api/a/events']:
            self.assertEqual(self.call(path)[0]['status'],401)
        self.assertEqual(self.call('/a/b')[0]['status'],404)
        self.assertEqual(self.call('/a/a','POST','password='+self.password,origin='https://evil.example')[0]['status'],403)
        self.login('a')
        for path in ['/arcade.js','/vendor/phaser.min.js']:
            meta,_=self.call(path,role='a')
            self.assertEqual(meta['status'],200)
            self.assertIn("script-src 'self';",meta['headers']['Content-Security-Policy'])
            self.assertIn("img-src 'self' data:;",meta['headers']['Content-Security-Policy'])
        self.assertEqual(self.call('/api/b/state',role='a')[0]['status'],401)
        self.assertEqual(self.call('/api/a/action','POST',dict(stage=0,kind='confirm'),role='a',csrf=False)[0]['status'],403)
        self.assertEqual(self.call('/api/a/archive',role='a')[0]['status'],403)
        self.assertEqual(self.call('/api/a/answer','POST',dict(stage=0,answer='2'),role='a')[0]['status'],404)
        self.assertEqual(self.act('a',0,'move',direction='down')[0]['status'],400)
        self.assertEqual(self.act('a',0,'confirm')[0]['status'],400)

    def test_full_cooperative_game_with_restart_and_final_gate(self):
        self.login('a');self.login('b');self.train();self.race();self.album();self.circuit()
        self.app=App(self.config,self.database)
        self.assertIn('fragment',self.state('a')['play']);self.assertNotIn('fragment',self.state('b')['play'])
        meta,archive=self.call('/api/b/archive',role='b');self.assertEqual(meta['status'],200)
        fragment=self.state('a')['play']['fragment']
        key=hashlib.sha256(f'{fragment}:{archive["salt"]}'.encode()).digest()
        plaintext=bytes(x^y for x,y in zip(bytes.fromhex(archive['cipher_hex']),key)).decode()
        self.assertEqual(plaintext,'13062019')
        receipt=hashlib.sha256((archive['salt']+':'+plaintext).encode()).hexdigest()
        self.assertEqual(self.act('b',3,'confirm',value=7,receipt='bad')[0]['status'],400)
        self.act('b',3,'confirm',value=7,receipt=receipt)
        self.assertEqual(self.state('a')['stage'],3)
        self.act('a',3,'confirm',word=receipt[:8].upper())
        self.assertEqual(self.state('a')['stage'],4)
        for position,step in [(4,1),(0,0),(True,1),(0,2)]:
            self.assertEqual(self.act('a',4,'rotate',position=position,step=step)[0]['status'],400)
        # Each mechanical ring turns independently and wraps; repeated values are legal.
        self.act('a',4,'rotate',position=0,step=1)
        self.assertEqual(self.state('a')['play']['order'],[0,1,0,2])
        self.assertEqual(self.act('a',4,'confirm')[0]['status'],400)
        for r in ['a','b']:
            for i in range(4):
                while self.state(r)['play']['order'][i]!=i:
                    self.assertEqual(self.act(r,4,'rotate',position=i,step=1)[0]['status'],200)
        self.act('a',4,'confirm');self.assertNotIn('code',self.state('a'))
        self.act('b',4,'rotate',position=0,step=-1)
        self.assertFalse(self.state('a')['solved'])
        self.assertEqual(self.act('b',4,'confirm')[0]['status'],400)
        self.act('b',4,'rotate',position=0,step=1)
        self.act('a',4,'confirm');self.act('b',4,'confirm');state=self.state('a')
        self.assertEqual(state['code'],'8247');self.assertTrue(state['complete']);self.assertEqual(len(state['rewards']),4)
        self.assertEqual(self.act('a',4,'confirm')[0]['status'],409)

    def test_no_plaintext_date_or_future_content_in_views(self):
        self.login('a');self.login('b')
        for r in ['a','b']:
            state=self.state(r)
            self.assertNotIn('code',state);self.assertNotIn('archive',state)
            self.assertNotIn('fragment',json.dumps(state));self.assertNotIn('blocked',state['play']) if r=='a' else None
        self.train();self.race();self.album();self.circuit()
        for r in ['a','b']:
            for _ in range(3):self.call(f'/api/{r}/hint','POST',dict(stage=3),role=r)
            for forbidden in ['2019-06-13','13.06.2019','13062019']:
                self.assertNotIn(forbidden,json.dumps(self.state(r)))
                self.assertNotIn(forbidden,json.dumps(self.game))
        self.assertNotIn('receipt',self.call('/api/b/archive',role='b')[1]['cipher_hex'])
        self.assertNotIn('13062019',json.dumps(self.call('/api/b/archive',role='b')[1]))

    def test_moving_after_confirmation_requires_both_to_confirm_again(self):
        self.login('a');self.login('b');self.train();self.race()
        for r in ['a','b']:
            for i in range(4):self.act(r,2,'place',item=i,position=i)
        self.act('a',2,'confirm');self.assertTrue(self.state('a')['solved'])
        self.act('a',2,'place',item=0,position=1)
        self.assertFalse(self.state('a')['solved'])
        self.assertEqual(self.act('b',2,'confirm')[0]['status'],400)

    def test_existing_train_position_survives_switch_upgrade(self):
        with self.app.db() as db:
            db.execute('INSERT OR REPLACE INTO runtime VALUES (1,0,?)',(json.dumps(dict(leg=1,position=4,done=False,last='Old mark',ping=3)),))
        self.login('a');state=self.login('b')
        self.assertEqual(state['play']['position'],4);self.assertEqual(state['play']['leg'],1)
        self.assertEqual(state['play']['driver'],'a');self.assertEqual(state['play']['motion'],'stopped')
        self.assertNotIn('ping',state['play'])
        self.assertEqual(self.act('b',0,'set_switch',node=4,direction='up')[0]['status'],200)
        self.assertEqual(self.state('a')['play']['signal'],'green')
        self.app=App(self.config,self.database)
        self.assertEqual(self.state('a')['play']['switch_direction'],'up')

    def test_internal_external_local_origins_share_state(self):
        origins='https://cup.home.localhost https://cup.betz.localhost'
        with patch.dict(os.environ,WEDDING_ORIGINS=origins):self.app=App(self.config,self.database)
        self.login('a',origins.split()[0]);self.login('b',origins.split()[1])
        meta,_=self.call('/api/a/action','POST',dict(stage=0,kind='set_switch',node=0,direction='down'),role='a',origin=origins.split()[0])
        self.assertEqual(meta['status'],200);self.assertEqual(self.state('b')['play']['switch_direction'],'down')
        self.assertEqual(self.call('/api/a/action','POST',dict(stage=0,kind='set_switch',node=0,direction='down'),role='a',origin='https://evil.example')[0]['status'],403)

    def test_hints_sse_logout_and_changed_config(self):
        self.login('a');self.login('b')
        for _ in range(5):self.call('/api/a/hint','POST',dict(stage=0),role='a')
        self.assertEqual(len(self.state('a')['hints']),3);self.assertEqual(self.state('b')['hints'],[])
        _,stream=self.call('/api/a/events',role='a',stream=True)
        self.assertIn(b'"stage": 0',next(stream))
        self.act('a',0,'set_switch',node=0,direction='down')
        with patch('server.time.sleep'):self.assertIn(b'"switch_direction": "down"',next(stream))
        self.call('/api/a/logout','POST',{},role='a')
        with patch('server.time.sleep'):self.assertIn(b'expired',next(stream))
        stream.close();self.assertEqual(self.call('/api/a/state',role='a')[0]['status'],401)
        config=json.loads(self.config.read_text());config['game']['title']='Other';self.config.write_text(json.dumps(config))
        with self.assertRaises(ValueError):App(self.config,self.database)

    def test_parallel_confirmations_advance_once(self):
        self.login('a');self.login('b')
        self.train(confirm=False)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results=list(pool.map(lambda r:self.act(r,0,'confirm'),['a','b','a','b']))
        self.assertTrue(all(meta['status'] in (200,409,400) for meta,_ in results));self.assertEqual(self.state('a')['stage'],1)


class EngineTest(unittest.TestCase):
    def setUp(self):self.game=make_game()
    def test_train_needs_both_roles_and_locks_switch_during_travel(self):
        state=initial(0)
        for role,data in [('b',dict(kind='set_switch',node=0,direction='down')),('a',dict(kind='throttle',node=0)),('b',dict(kind='move',direction='down')),('a',dict(kind='ping',node=3)),('b',dict(kind='throttle',node=0))]:
            with self.assertRaises(GameError):command(self.game,0,state,role,data,100)
        command(self.game,0,state,'a',dict(kind='set_switch',node=0,direction='right'),100)
        self.assertEqual(view(self.game,0,state,'b',100)['signal'],'red')
        with self.assertRaises(GameError):command(self.game,0,state,'b',dict(kind='throttle',node=0),100)
        command(self.game,0,state,'a',dict(kind='set_switch',node=0,direction='down'),100)
        command(self.game,0,state,'b',dict(kind='throttle',node=0),100)
        self.assertEqual(state['position'],0)
        with self.assertRaises(GameError):command(self.game,0,state,'a',dict(kind='set_switch',node=0,direction='right'),100.5)
        with self.assertRaises(GameError):command(self.game,0,state,'a',dict(kind='brake'),100.5)
        command(self.game,0,state,'b',dict(kind='brake'),100.5)
        advance(0,state,200,'a');self.assertEqual(state['position'],0)
        with self.assertRaises(GameError):command(self.game,0,state,'a',dict(kind='set_switch',node=0,direction='right'),200)
        command(self.game,0,state,'b',dict(kind='throttle',node=0),200)
        advance(0,state,200+TRAIN_SECONDS,'a')
        self.assertEqual(state['position'],3);self.assertIsNone(state['switch_direction']);self.assertEqual(state['motion'],'stopped')
        with self.assertRaises(GameError):command(self.game,0,state,'b',dict(kind='throttle',node=0),203)
        with self.assertRaises(GameError):command(self.game,0,state,'b',dict(kind='throttle',node=3),203)
        self.assertNotIn('blocked',view(self.game,0,state,'a',203))

    def test_snake_score_stamps_and_collision_are_authoritative(self):
        state=initial(1);w=state['snakes']['a']
        for _ in range(5):snake_tick(w,'a',state)
        self.assertEqual(w['score'],1);self.assertTrue(state['passport'][0])
        w['pending']='up'
        for _ in range(4):snake_tick(w,'a',state)
        self.assertEqual(w['score'],2);self.assertEqual(w['held'],[1]);self.assertFalse(state['passport'][1])
        command(self.game,1,state,'a',dict(kind='send'),1) if state['phase']=='race' else None
        state['phase']='race';command(self.game,1,state,'a',dict(kind='send'),1)
        self.assertTrue(state['passport'][1]);self.assertEqual(w['held'],[])
        w['direction']='up'
        for _ in range(6):snake_tick(w,'a',state)
        self.assertEqual(w['score'],2)
        self.assertEqual(w['index'],2)
        with self.assertRaises(GameError):command(self.game,1,state,'a',dict(kind='score',score=9999),1)

    def test_race_pauses_without_partner_and_keeps_fair_clock(self):
        state=initial(1)
        command(self.game,1,state,'a',dict(kind='ready'),100)
        command(self.game,1,state,'b',dict(kind='ready'),100)
        advance(1,state,103,'a');advance(1,state,103,'b')
        advance(1,state,104,'a');advance(1,state,104,'b')
        elapsed=state['elapsed'];advance(1,state,120,'a')
        self.assertTrue(state['paused']);self.assertEqual(state['elapsed'],elapsed)
        advance(1,state,120,'b');advance(1,state,121,'a')
        self.assertFalse(state['paused']);self.assertEqual(state['elapsed'],elapsed+1)

    def test_switch_logic_has_one_solution_and_separate_controls(self):
        import itertools
        solutions=[list(x) for x in itertools.product([False,True],repeat=4) if x[0]==x[2] and not x[1] and x[0]!=x[3] and sum(x)==2]
        self.assertEqual(solutions,[[True,False,True,False]])
        with self.assertRaises(GameError):command(self.game,3,initial(3),'b',dict(kind='switch',index=0),1)

if __name__=='__main__':unittest.main()
