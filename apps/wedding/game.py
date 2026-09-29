"""CUP v2: private personalization, public rules, no plaintext relationship date."""
import hashlib
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
        stage('Du navigierst. Ich fahre.', 'Zwei Rollen. Ein gemeinsamer Zug.',4,['Einstieg','9'],
            f"Du stellst die Weiche im Stellwerk. {p['b']} bedient Gas und Bremse und kennt die Sperren. Frage nach einem freien Gleis und stelle dann die Fahrtrichtung ein.",
            f"Du bedienst Gas und Bremse. {p['a']} stellt die Weiche. Melde die Sperren, prüfe das Signal und gib Gas. An jedem Halt stoppt der Zug automatisch. Am Zwischenziel tauscht ihr die Rollen.",
            ['Du stellst die Weiche am aktuellen Halt. Dein Gegenüber bedient Gas und Bremse.', 'Frage den Fahrer nach gesperrten Richtungen, bevor du die Weiche stellst.', 'Ein sicherer Weg: A → D → E → H → I. Zurück: I → F → E → B → A.'],
            ['Du bedienst Gas und Bremse. Die Fahrtrichtung legt das Stellwerk fest.', 'Nenne deinem Gegenüber die Sperren. Fahre erst bei grünem Signal; an jedem Halt stoppt der Zug automatisch.', 'Ein sicherer Weg: A → D → E → H → I. Zurück: I → F → E → B → A.']),
        stage('Der Japan-CUP', 'Ein kleiner Wettkampf. Ein gemeinsamer Reisepass.',5,['Japan','5'],
            'Sammelt mit eurer Schlange Reisestationen. Ihr habt dieselbe Geschwindigkeit und drei Minuten Zeit. Manche Stempel gehören deinem Gegenüber: Schicke sie weiter, damit euer gemeinsamer Reisepass voll wird.',
            'Sammelt mit eurer Schlange Reisestationen. Ihr habt dieselbe Geschwindigkeit und drei Minuten Zeit. Manche Stempel gehören deinem Gegenüber: Schicke sie weiter, damit euer gemeinsamer Reisepass voll wird.',
            ['Übe zuerst ohne Punkte. Steuere mit den Richtungstasten oder wische über das Spielfeld.', 'Eine Kollision bringt dich zum letzten Abschnitt zurück. Deine Punkte und Stempel bleiben erhalten.', 'Nach dem Rennen könnt ihr fehlende Stationen zusammen ergänzen. Die eingeblendete Reisehilfe nennt bei Bedarf den nächsten Halt.'],
            ['Übe zuerst ohne Punkte. Benutze die Pfeiltasten oder die Tasten unter dem Spielfeld.', 'Eine Kollision bringt dich zum letzten Abschnitt zurück. Deine Punkte und Stempel bleiben erhalten.', 'Nach dem Rennen könnt ihr fehlende Stationen zusammen ergänzen. Die eingeblendete Reisehilfe nennt bei Bedarf den nächsten Halt.']),
        stage('Zwei Ansichten, ein Album', 'Wieder im selben Team.',6,[p['honeymoon'],'2'],
            f"Ordne die vier Bildkarten. {p['b']} ordnet die passenden Beschriftungen. Ihr seht eure Änderungen sofort, aber nicht den Inhalt der anderen Seite. Beschreibt einander, was auf welchen Platz gehört.",
            f"Ordne die vier Beschriftungen. {p['a']} hat die Bildkarten und weitere Hinweise. Die Änderungen sind auf beiden Seiten sichtbar. Einigt euch auf die vier Plätze.",
            ['Die Orte sind beschriftet. Die Bilder sind Illustrationen, keine behaupteten Urlaubsfotos.', 'Die Insel liegt unter Tokio. Kyoto liegt rechts von Tokio. Frage nach der Lage der noch kommenden Reise.', f'Oben: Tokio und Kyoto. Unten: Amami und {p["honeymoon"]}.'],
            ['Deine Beschriftungen gehören zu den vier Bildern der anderen Seite.', 'Die zukünftige Reise liegt unter Kyoto. Tokio gehört nach oben links.', f'Oben: Tokio und Kyoto. Unten: Amami und {p["honeymoon"]}.']),
        stage('Das Bierdiplom gilt hier nicht', 'Zusammen schalten. Zusammen entschlüsseln.',8,['Anfang',str(value)],
            f"Ihr bedient dasselbe Schaltpult. Du kannst A und B schalten; {p['b']} kann C und D schalten. Deine Bedingungen stehen unten. Tauscht eure Hinweise aus und prüft danach beide die Schaltung.",
            f"Ihr bedient dasselbe Schaltpult. Du kannst C und D schalten; {p['a']} kann A und B schalten. Danach öffnest du das verschlüsselte Archiv mit dem Schlüssel deiner Mitspielerin.",
            ['Deine Bedingungen reichen nicht allein aus. Beide Seiten dürfen jeweils zwei Schalter bedienen.', 'A und C stehen gleich. B bleibt aus. Frage, wie viele Schalter insgesamt eingeschaltet sein müssen.', 'Die Stellung lautet: A ein, B aus, C ein, D aus. Danach bekommt dein Gegenüber die Datei und du den Schlüssel.'],
            ['Deine Bedingungen reichen nicht allein aus. Beide Seiten dürfen jeweils zwei Schalter bedienen.', 'A und D stehen verschieden. Insgesamt müssen genau zwei Schalter eingeschaltet sein.', 'Die Stellung lautet: A ein, B aus, C ein, D aus. Der SHA-256-Schlüssel entsteht aus Schlüsselteil:Daten-Salz. XOR entschlüsselt acht ASCII-Ziffern; berechne Tag minus Monat und das Prüfwort.']),
        stage('Unser gemeinsamer Schlüssel', 'Der CUP hat einen Sieger. Die Box braucht euch beide.',5,None,
            f"Du hast die vier Erinnerungsstücke und ihre Zahlen. {p['b']} kennt ihre Reihenfolge. Ordne deine Karten nach seinen Hinweisen. Erst wenn ihr beide die vier Ringe bestätigt, öffnet sich das Schloss.",
            f"Du ordnest die vier Kapitel am Schloss. {p['a']} hat die Erinnerungsstücke mit den Zahlen. Erkläre ihr die Reihenfolge und stimme deine Kapitel darauf ab. Bestätigt zum Schluss beide.",
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
