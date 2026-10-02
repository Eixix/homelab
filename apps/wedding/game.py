"""CUP v2: private personalization, public rules, no plaintext relationship date."""
import hashlib
import hmac
import copy
import secrets
from datetime import date


def make_game(personal=None):
    p = dict(a='Person A', b='Person B', date='', boarding='Einstieg', destination='Zielort',
             honeymoon='Nächste Reise', greeting='Alles Gute für euer gemeinsames Leben!',
             relationship_date='2019-06-13', trip_route=[f'Station {i+1}' for i in range(11)])
    p.update(personal or {})
    route = p['trip_route']
    if len(route) != 11 or not all(isinstance(x,str) and x.strip() for x in route):
        raise ValueError('Der Japan-CUP benötigt elf Reisestationen.')
    relationship = date.fromisoformat(p['relationship_date'])
    plaintext = relationship.strftime('%d%m%Y').encode()
    fragment, salt = secrets.token_hex(16), secrets.token_hex(12)
    key = hashlib.sha256(f'{fragment}:{salt}'.encode()).digest()
    cipher = bytes(a ^ b for a,b in zip(plaintext,key)).hex()
    receipt = hashlib.sha256(salt.encode()+b':'+plaintext).hexdigest()
    value = abs(relationship.day-relationship.month) % 10
    def stage(title, subtitle, minutes, reward, a, b, ha, hb):
        return dict(title=title,subtitle=subtitle,minutes=minutes,reward=reward,copy={'a':a,'b':b},hints={'a':ha,'b':hb})
    stages = [
        stage('Die Zugfahrt', 'Fahrt von Weißenhorn nach Zürich und zurück',4,['Einstieg','9'],
            f"Du stellst die Weiche im Stellwerk. {p['b']} bedient Gas und Bremse und kennt die Sperren. Frage nach einem freien Gleis und stelle dann die Fahrtrichtung ein.",
            f"Du bedienst Gas und Bremse. {p['a']} stellt die Weiche. Melde die Sperren, prüfe das Signal und gib Gas. An jedem Halt stoppt der Zug automatisch. Am Zwischenziel tauscht ihr die Rollen.",
            ['Du stellst die Weiche am aktuellen Halt. Dein Gegenüber bedient Gas und Bremse.', 'Frage den Fahrer nach gesperrten Richtungen, bevor du die Weiche stellst.', 'Ein sicherer Weg: Weißenhorn → Memmingen → Lindau → St. Gallen → Zürich. Zurück: Zürich → Winterthur → Lindau → Ulm → Weißenhorn.'],
            ['Du bedienst Gas und Bremse. Die Fahrtrichtung legt das Stellwerk fest.', 'Nenne deinem Gegenüber die Sperren. Fahre erst bei grünem Signal; an jedem Halt stoppt der Zug automatisch.', 'Ein sicherer Weg: Weißenhorn → Memmingen → Lindau → St. Gallen → Zürich. Zurück: Zürich → Winterthur → Lindau → Ulm → Weißenhorn.']),
        stage('Japan-CUP', 'Sammelt Reisestationen für euren Reisepass',5,['Japan','5'],
            'Wer mehr Reisestationen einsammelt, gewinnt den CUP. Manche Stempel gehören dem anderen – schickt sie weiter. Nach dem Rennen ergänzt ihr gemeinsam die fehlenden Stationen im Reisepass.',
            'Wer mehr Reisestationen einsammelt, gewinnt den CUP. Manche Stempel gehören dem anderen – schickt sie weiter. Nach dem Rennen ergänzt ihr gemeinsam die fehlenden Stationen im Reisepass.',
            ['In der Proberunde zählen keine Punkte. Wische auf dem Spielfeld oder tippe die Richtungstasten.', 'Bei einer Kollision startet deine Schlange wieder am Anfang. Punkte und Stempel bleiben erhalten.', 'Nach dem Rennen könnt ihr fehlende Stationen ergänzen. Der nächste fehlende Halt wird dann angezeigt.'],
            ['In der Proberunde zählen keine Punkte. Wische auf dem Spielfeld oder tippe die Richtungstasten.', 'Bei einer Kollision startet deine Schlange wieder am Anfang. Punkte und Stempel bleiben erhalten.', 'Nach dem Rennen könnt ihr fehlende Stationen ergänzen. Der nächste fehlende Halt wird dann angezeigt.']),
        stage('Das Fotoalbum', 'Ordnet Bilder und Beschriftungen zu',6,[p['honeymoon'],'2'],
            f"Du ordnest vier Bilder. {p['b']} hat die Beschriftungen. Beschreibt einander eure Karten und wählt für jedes Paar denselben Platz.",
            f"Du ordnest vier Beschriftungen. {p['a']} hat die Bilder. Beschreibt einander eure Karten und wählt für jedes Paar denselben Platz.",
            ['Die Orte sind beschriftet. Die Bilder sind Illustrationen, keine behaupteten Urlaubsfotos.', 'Die Insel liegt unter Tokio. Kyoto liegt rechts von Tokio. Frage nach der Lage der noch kommenden Reise.', f'Oben: Tokio und Kyoto. Unten: Amami und {p["honeymoon"]}.'],
            ['Deine Beschriftungen gehören zu den vier Bildern der anderen Seite.', 'Die zukünftige Reise liegt unter Kyoto. Tokio gehört nach oben links.', f'Oben: Tokio und Kyoto. Unten: Amami und {p["honeymoon"]}.']),
        stage('Das Schaltpult', 'Tauscht Hinweise aus und öffnet das Archiv',8,['Anfang',str(value)],
            f"Du bedienst A und B, {p['b']} C und D. Tauscht eure Bedingungen aus, stellt die Schalter ein und prüft beide die Schaltung. Danach gibst du {p['b']} den Schlüsselteil.",
            f"Du bedienst C und D, {p['a']} A und B. Tauscht eure Bedingungen aus und prüft beide die Schaltung. Danach öffnest du mit ihrem Schlüsselteil das verschlüsselte Archiv und gibst ihr das Prüfwort.",
            ['Deine Bedingungen reichen nicht allein aus. Beide Seiten dürfen jeweils zwei Schalter bedienen.', 'A und C stehen gleich. B bleibt aus. Frage, wie viele Schalter insgesamt eingeschaltet sein müssen.', 'Die Stellung lautet: A ein, B aus, C ein, D aus. Danach bekommt dein Gegenüber die Datei und du den Schlüssel.'],
            ['Deine Bedingungen reichen nicht allein aus. Beide Seiten dürfen jeweils zwei Schalter bedienen.', 'A und D stehen verschieden. Insgesamt müssen genau zwei Schalter eingeschaltet sein.', 'Die Stellung lautet: A ein, B aus, C ein, D aus. Der SHA-256-Schlüssel entsteht aus Schlüsselteil:Daten-Salz. XOR entschlüsselt acht ASCII-Ziffern; berechne Tag minus Monat und das Prüfwort.']),
        stage('Die Schlüsselbox', 'Bringt Zahlen und Kapitel in die richtige Reihenfolge',5,None,
            f"Deine Erinnerungsstücke liefern die vier Zahlen. {p['b']} kennt ihre Reihenfolge. Vergleicht eure Hinweise und stellt beide Boxhälften passend ein. Bestätigt zum Schluss gemeinsam.",
            f"Du kennst die Reihenfolge der vier Kapitel. {p['a']} hat die Zahlen dazu. Vergleicht eure Hinweise und stellt beide Boxhälften passend ein. Bestätigt zum Schluss gemeinsam.",
            ['Jede Karte stammt aus einer der bisherigen Etappen.', 'Dein Gegenüber kennt die Reihenfolge. Beschreibe die Namen deiner vier Erinnerungsstücke.', f'Die Reihenfolge lautet Japan, Einstieg, {p["honeymoon"]}, Anfang.'],
            ['Du ordnest Kapitel, keine Ziffern. Die Zahlen besitzt dein Gegenüber.', 'Beginne mit der großen Reise. Danach kommt der gemeinsame Einstieg, dann die nächste Reise und zuletzt euer Anfang.', f'Die Reihenfolge lautet Japan, Einstieg, {p["honeymoon"]}, Anfang.'])
    ]
    return dict(schema=2,title='CUP · Team Ehe',names={'a':p['a'],'b':p['b']},date=p['date'],greeting=p['greeting'],
                destination=p['destination'],boarding=p['boarding'],honeymoon=p['honeymoon'],route=route,
                code=''.join(stages[i]['reward'][1] for i in (1,0,2,3)),stages=stages,
                archive=dict(fragment=fragment,salt=salt,cipher_hex=cipher,receipt=receipt,value=value))


def previous_pin_game(game):
    """Reconstruct only the previous PIN mapping for a narrow progress-preserving migration."""
    old = copy.deepcopy(game)
    if old['code'] != '592' + str(old['archive']['value']):
        raise ValueError('Unerwartete neue PIN-Konfiguration.')
    for index, digit in enumerate(('2', '8', '4')):
        old['stages'][index]['reward'][1] = digit
    old['code'] = '824' + str(old['archive']['value'])
    return old


def gallery_key(config):
    """Derive an independent gallery key from the existing private password verifier."""
    digest = bytes.fromhex(config['password_hash'].split('$')[2])
    if len(digest) != 64:
        raise ValueError('Ungültiger privater Passworthash.')
    return hmac.digest(digest, b'cup/gallery/v2', hashlib.sha256)
