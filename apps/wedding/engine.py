"""Authoritative two-role game engine. Client commands cannot supply scores or solutions."""
import copy
import hashlib
import hmac

DIRECTIONS = {'up':(0,-1),'right':(1,0),'down':(0,1),'left':(-1,0)}
OPPOSITE = {'up':'down','down':'up','left':'right','right':'left'}
TARGETS = [(9,6),(9,2),(2,2),(2,9),(9,9),(6,9),(6,3),(10,3),(10,10),(3,10),(3,4)]
BLOCKED = [{(0,1),(1,2),(4,5),(5,8)}, {(7,8),(3,6),(2,5),(3,4)}]
TRAIN_STOPS = ('Weißenhorn','Ulm','München','Memmingen','Lindau','Winterthur','Bregenz','St. Gallen','Zürich')
RACE_SECONDS = 180
TICK = .24
TRAIN_SECONDS = 2.0
TRAIN_HINTS = {
 'signal': ['Du stellst die Weiche am aktuellen Halt. Dein Gegenüber bedient Gas und Bremse.', 'Frage den Fahrer nach gesperrten Richtungen, bevor du die Weiche stellst.', 'Ein sicherer Weg: Weißenhorn → Memmingen → Lindau → St. Gallen → Zürich. Zurück: Zürich → Winterthur → Lindau → Ulm → Weißenhorn.'],
 'driver': ['Du bedienst Gas und Bremse. Die Fahrtrichtung legt das Stellwerk fest.', 'Nenne deinem Gegenüber die Sperren. Fahre erst bei grünem Signal; an jedem Halt stoppt der Zug automatisch.', 'Ein sicherer Weg: Weißenhorn → Memmingen → Lindau → St. Gallen → Zürich. Zurück: Zürich → Winterthur → Lindau → Ulm → Weißenhorn.']
}


class GameError(ValueError):
    pass


def snake_world():
    return dict(body=[[4,6],[3,6],[2,6]],direction='right',pending=None,index=0,target=list(TARGETS[0]),score=0,held=[],cooldown=0,acc=0,practice=False,practiced=False,practice_ticks=0)


def snake_target(w):
    for offset in range(len(TARGETS)):
        target=list(TARGETS[(w['index']+offset)%len(TARGETS)])
        if target not in w['body']: return target
    for y in range(12):
        for x in range(12):
            if [x,y] not in w['body']: return [x,y]
    return None


def initial(stage):
    if stage==0: return dict(leg=0,position=0,done=False,switch_direction=None,motion='stopped',travel=None,last='Das Stellwerk stellt zuerst die Weiche. Danach gibt der Fahrer Gas.')
    if stage==1: return dict(phase='warmup',ready={'a':False,'b':False},snakes={r:snake_world() for r in ('a','b')},passport=[False]*11,elapsed=0,last=None,heartbeat={'a':0,'b':0},winner=None,last_action='Noch läuft die Proberunde. Hier zählt nichts.')
    if stage==2: return dict(photos=[2,0,3,1],captions=[1,3,0,2],last_action='Vier Bilder suchen vier Plätze.')
    if stage==3: return dict(switches=[False]*4,armed={'a':False,'b':False},unlocked=False,last_action='Das Bierdiplom ist anerkannt. Für diese Schaltung braucht ihr trotzdem beide.')
    if stage==4: return dict(cards=[3,1,0,2],chapters=[2,0,3,1],last_action='Vier Erinnerungsstücke. Ein gemeinsames Schloss.')
    return {}


def collide(w):
    w['body']=[[4,6],[3,6],[2,6]]
    w['direction']='right';w['pending']=None;w['cooldown']=3
    w['target']=snake_target(w)


def snake_tick(w,role,state,practice=False):
    if w['cooldown']:
        w['cooldown']-=1
        return
    if w['pending']:
        w['direction']=w['pending'];w['pending']=None
    dx,dy=DIRECTIONS[w['direction']]
    x,y=w['body'][0];head=[x+dx,y+dy]
    target=w.get('target')
    if target is None or target in w['body']:
        target=w['target']=snake_target(w)
    eating=head==target
    body=w['body'] if eating else w['body'][:-1]
    if not (0<=head[0]<12 and 0<=head[1]<12) or head in body:
        collide(w)
        return
    w['body'].insert(0,head)
    if not eating: w['body'].pop()
    if eating:
        index=w['index'] % 11
        w['index']+=1
        w['target']=snake_target(w)
        if practice: return
        w['score']+=1
        owner='a' if index%2==0 else 'b'
        if owner==role: state['passport'][index]=True
        elif index not in w['held'] and not state['passport'][index]: w['held'].append(index)


def advance(stage,state,now,role):
    if stage==0:
        travel=state.get('travel')
        if state.get('motion')=='moving' and travel and now>=travel['arrives_at']:
            state['position']=travel['target'];state['travel']=None;state['motion']='stopped';state['switch_direction']=None
            state['last']=f"{TRAIN_STOPS[state['position']]} erreicht. Der Zug hält; das Stellwerk stellt die nächste Weiche."
            goal=8 if state['leg']==0 else 0
            if state['position']==goal:
                if state['leg']==0:
                    state['leg']=1;state['last']='Zwischenziel erreicht. Tauscht Stellwerk und Führerstand.'
                else:
                    state['done']=True;state['last']='Beide Fahrten geschafft. Bestätigt jetzt gemeinsam.'
        return
    if stage!=1: return
    previous=state['last']
    dt=max(0,min(now-previous,2)) if previous is not None else 0
    state['last']=now
    state['heartbeat'][role]=now
    if state['phase']=='warmup':
        for r,w in state['snakes'].items():
            if not w['practice']: continue
            w['acc']+=dt
            while w['acc']>=TICK:
                w['acc']-=TICK;snake_tick(w,r,state,True);w['practice_ticks']+=1
            if w['practice_ticks']>=60:
                w['practice']=False;w['practiced']=True
        return
    if state['phase']=='countdown':
        if now>=state['starts_at']:
            state['phase']='race';state['last']=now
        return
    if state['phase']!='race': return
    # Both pages must be connected. A missing partner pauses the clock and both snakes.
    paused=any(now-stamp>5 for stamp in state['heartbeat'].values())
    state['paused']=paused
    if paused: return
    dt=min(dt,max(0,RACE_SECONDS-state['elapsed']))
    state['elapsed']+=dt
    for r,w in state['snakes'].items():
        w['acc']+=dt
        while w['acc']+1e-9>=TICK:
            w['acc']-=TICK;snake_tick(w,r,state)
    if state['elapsed']>=RACE_SECONDS:
        state['phase']='passport'
        a,b=state['snakes']['a']['score'],state['snakes']['b']['score']
        state['winner']='a' if a>b else 'b' if b>a else 'tie'
        state['last_action']='Das Rennen ist vorbei. Jetzt vervollständigt ihr gemeinsam den Reisepass.'


def require(condition,message):
    if not condition: raise GameError(message)


def command(game,stage,state,role,data,now):
    kind=data.get('kind')
    partner='b' if role=='a' else 'a'
    if stage==0:
        require(kind in ('set_switch','throttle','brake','confirm'),'Stellt die Weiche im Stellwerk und fahrt mit Gas und Bremse.')
        if kind=='confirm':
            require(state['done'],'Bringt den Zug zuerst gemeinsam ans Ziel.')
            return True
        require(not state['done'],'Ihr seid bereits angekommen. Bestätigt beide die Fahrt.')
        driver='b' if state['leg']==0 else 'a'
        if kind=='brake':
            require(role==driver,'Die Bremse bedient der Fahrer.')
            require(state.get('motion')=='moving','Der Zug steht bereits.')
            state['travel']['remaining']=max(.01,state['travel']['arrives_at']-now)
            state['motion']='paused';state['last']='Der Fahrer hat gebremst. Mit Gas setzt er die Fahrt fort.'
            return False
        require(type(data.get('node')) is int and data['node']==state['position'],'Ihr seid inzwischen an einem anderen Halt. Wartet auf den aktuellen Spielstand.')
        if kind=='set_switch':
            require(role!=driver,'Die Weiche stellt dein Gegenüber im Stellwerk.')
            require(state.get('motion','stopped')=='stopped' and not state.get('travel'),'Während der Fahrt bleibt die Weiche verriegelt.')
            direction=data.get('direction');require(direction in DIRECTIONS,'Wähle eine Weichenrichtung.')
            dx,dy=DIRECTIONS[direction];pos=state['position'];nx,ny=pos%3+dx,pos//3+dy
            require(0<=nx<3 and 0<=ny<3,'In diese Richtung liegt kein Gleis.')
            state['switch_direction']=direction
            state['last']=f"Das Stellwerk hat die Weiche bei {chr(65+pos)} gestellt. Der Fahrer prüft das Signal."
            return False
        require(role==driver,'Gas gibt dein Gegenüber im Führerstand.')
        require(state.get('motion')!='moving','Der Zug fährt bereits. Am nächsten Halt stoppt er automatisch.')
        if state.get('motion')=='paused':
            state['travel']['arrives_at']=now+state['travel']['remaining'];state['motion']='moving'
            state['last']='Der Fahrer setzt die Fahrt fort.'
            return False
        direction=state.get('switch_direction')
        require(direction in DIRECTIONS,'Das Stellwerk muss zuerst die Weiche stellen.')
        dx,dy=DIRECTIONS[direction];pos=state['position'];nx,ny=pos%3+dx,pos//3+dy
        require(0<=nx<3 and 0<=ny<3,'Diese Weiche führt an den Rand des Spielplans.')
        target=ny*3+nx
        require(tuple(sorted((pos,target))) not in BLOCKED[state['leg']],'Rotes Signal: Diese Strecke ist gesperrt. Bitte das Stellwerk um eine andere Weichenstellung.')
        state['travel']=dict(target=target,arrives_at=now+TRAIN_SECONDS,remaining=TRAIN_SECONDS)
        state['motion']='moving';state['last']='Der CUP Express fährt. Die Weiche bleibt bis zum nächsten Halt verriegelt.'
        return False
    if stage==1:
        w=state['snakes'][role]
        if kind=='practice':
            require(state['phase']=='warmup' and not state['ready'][role],'Die Proberunde ist bereits vorbei.')
            state['snakes'][role]=snake_world();state['snakes'][role]['practice']=True
        elif kind=='ready':
            require(state['phase']=='warmup','Ihr seid bereits startbereit.')
            state['ready'][role]=True;w['practice']=False
            if all(state['ready'].values()):
                state['phase']='countdown';state['starts_at']=now+3;state['snakes']={r:snake_world() for r in ('a','b')}
        elif kind=='turn':
            require(state['phase']=='race' or w['practice'],'Starte zuerst die Proberunde oder das Rennen.')
            direction=data.get('direction');require(direction in DIRECTIONS,'Wähle eine Richtung.')
            require(direction!=OPPOSITE[w['direction']],'Die Schlange kann nicht direkt rückwärts fahren.')
            if w['pending'] is None: w['pending']=direction
        elif kind=='send':
            require(state['phase'] in ('race','passport'),'Stempel können erst im Wettkampf gesammelt werden.')
            require(bool(w['held']),'Du hast gerade keine Stempel zum Weiterschicken.')
            for index in w['held']: state['passport'][index]=True
            w['held']=[];state['last_action']=f"{game['names'][role]} hat Stempel weitergeschickt."
        elif kind=='stamp':
            require(state['phase']=='passport','Ergänzt den Reisepass erst nach dem Rennen.')
            missing=next((i for i,done in enumerate(state['passport']) if not done),None)
            require(missing is not None,'Der Reisepass ist bereits vollständig.')
            owner='a' if missing%2==0 else 'b'
            require(role==owner,'Diese Station ergänzt dein Gegenüber. Helft euch mit der Reihenfolge.')
            require(type(data.get('station')) is int and data['station']==missing,'Diese Station kommt an einer anderen Stelle. Sprecht über die Reihenfolge eurer Reise.')
            state['passport'][missing]=True;state['last_action']=f"{game['names'][role]} hat eine Reisestation ergänzt."
        elif kind=='confirm':
            require(state['phase']=='passport' and all(state['passport']),'Vervollständigt zuerst euren gemeinsamen Reisepass.')
            return True
        else: raise GameError('Diese Aktion passt nicht zum Japan-CUP.')
        return False
    if stage in (2,4):
        field=('photos' if role=='a' else 'captions') if stage==2 else ('cards' if role=='a' else 'chapters')
        if kind=='rotate' and stage==4:
            position,step=data.get('position'),data.get('step')
            require(type(position) is int and position in range(4) and type(step) is int and step in (-1,1),'Wähle einen der vier Ringe und eine Drehrichtung.')
            state[field][position]=(state[field][position]+step)%4
            state['last_action']=f"{game['names'][role]} hat Ring {position+1} gedreht."
        elif kind=='place':
            item,position=data.get('item'),data.get('position')
            require(type(item) is int and type(position) is int and item in range(4) and position in range(4),'Wähle eine Karte und einen der vier Plätze.')
            if stage==4: state[field][position]=item
            else:
                old=state[field].index(item);state[field][old],state[field][position]=state[field][position],state[field][old]
            state['last_action']=f"{game['names'][role]} hat {'ein Bild' if stage==2 and role=='a' else 'eine Beschriftung' if stage==2 else 'einen Ring'} verschoben."
        elif kind=='confirm':
            fields=('photos','captions') if stage==2 else ('cards','chapters')
            require(all(state[f]==list(range(4)) for f in fields),'Die beiden Seiten passen noch nicht zusammen. Vergleicht eure Anordnung und die Hinweise.')
            return True
        else: raise GameError('Wähle eine Karte aus und setze sie auf einen Platz.')
        return False
    if stage==3:
        if kind=='switch':
            index=data.get('index');require(type(index) is int and index in ((0,1) if role=='a' else (2,3)),'Diesen Schalter bedient dein Gegenüber.')
            require(not state['unlocked'],'Die Schaltung ist bereits geprüft und bleibt jetzt geschlossen.')
            state['switches'][index]=not state['switches'][index];state['armed']={'a':False,'b':False}
            state['last_action']=f"{game['names'][role]} hat Schalter {chr(65+index)} {'eingeschaltet' if state['switches'][index] else 'ausgeschaltet'}."
        elif kind=='check':
            require(state['switches']==[True,False,True,False],'Diese Stellung erfüllt noch nicht alle Bedingungen. Vergleicht eure Hinweise.')
            state['armed'][role]=True
            if all(state['armed'].values()):
                state['unlocked']=True;state['last_action']='Schaltung geprüft. Tauscht jetzt Schlüssel und Prüfwort aus.'
        elif kind=='confirm':
            require(state['unlocked'],'Prüft zuerst beide die gemeinsame Schaltung.')
            archive=game['archive']
            if role=='a':
                word=str(data.get('word','')).strip().upper()
                require(hmac.compare_digest(word,archive['receipt'][:8].upper()),'Das Prüfwort stimmt noch nicht. Lass es dir von deinem Gegenüber nennen.')
            else:
                receipt=str(data.get('receipt','')).strip().lower()
                require(type(data.get('value')) is int and data['value']==archive['value'] and hmac.compare_digest(receipt,archive['receipt']),'Die Entschlüsselung stimmt noch nicht. Prüfe den Schlüssel und das Dateiformat.')
            return True
        else: raise GameError('Diese Aktion passt nicht zum Schaltpult.')
        return False
    raise GameError('Das Spiel ist bereits abgeschlossen.')


def view(game,stage,state,role,now=None):
    result=copy.deepcopy(state)
    if stage==0:
        driver='b' if state['leg']==0 else 'a';pos=state['position']
        result.pop('ping',None);result['driver']=driver;result['goal']=8 if state['leg']==0 else 0
        result['stops']=TRAIN_STOPS
        result['switch_direction']=state.get('switch_direction');result['motion']=state.get('motion','stopped');result['travel']=state.get('travel')
        result['tracks']=[];blocked=[]
        for name,(dx,dy) in DIRECTIONS.items():
            x,y=pos%3+dx,pos//3+dy
            if 0<=x<3 and 0<=y<3: result['tracks'].append(name)
            if not (0<=x<3 and 0<=y<3) or tuple(sorted((pos,y*3+x))) in BLOCKED[state['leg']]: blocked.append(name)
        travel=result['travel']
        result['travel_progress']=max(0,min(1,1-(travel['remaining'] if result['motion']=='paused' else max(0,travel['arrives_at']-(now or 0)))/TRAIN_SECONDS)) if travel else 0
        result['signal']='unset' if not result['switch_direction'] else 'red' if result['switch_direction'] in blocked else 'green'
        if role==driver: result['blocked']=blocked
        else: result.pop('signal')
        return result
    if stage==1:
        own=state['snakes'][role];peer=state['snakes']['b' if role=='a' else 'a']
        result=dict(phase=state['phase'],ready=state['ready'],body=own['body'],direction=own['direction'],index=own['index'],cooldown=own['cooldown'],score=own['score'],peer_score=peer['score'],held=len(own['held']),
                    practice=own['practice'],practiced=own['practiced'],remaining=max(0,int(RACE_SECONDS-state['elapsed']+.999)),paused=state.get('paused',False),
                    target=own.get('target') or snake_target(own),station=game['route'][own['index']%11],target_owner='a' if own['index']%11%2==0 else 'b',
                    countdown=max(0,int(state.get('starts_at',0)-state.get('last',0)+.999)),passport=state['passport'],route=game['route'],winner=state['winner'],last_action=state['last_action'])
        missing=next((i for i,x in enumerate(state['passport']) if not x),None)
        result['missing']=missing;result['stamp_role']=('a' if missing%2==0 else 'b') if missing is not None else None
        return result
    if stage in (2,4):
        own=('photos' if role=='a' else 'captions') if stage==2 else ('cards' if role=='a' else 'chapters')
        peer=('captions' if role=='a' else 'photos') if stage==2 else ('chapters' if role=='a' else 'cards')
        result=dict(order=state[own],peer_positions=state[peer],last_action=state['last_action'],matched=[state[own][i]==state[peer][i]==i for i in range(4)])
        # IDs on the other side are deliberately masked; only the movement is visible.
        result['peer_positions']=([state[peer].index(i) for i in [3,0,2,1]] if stage==2
                                  else [{3:0,0:1,2:2,1:3}[item] for item in state[peer]])
        if stage==2:
            result['labels']=['Tokio','Kyoto','Amami',game['honeymoon']] if role=='a' else ['Unsere erste und letzte Japanstation','Die Stadt direkt nach Tokio','Die Insel vor der Rückkehr','Unsere nächste Reise']
            result['rules']=['Die Insel liegt unter Tokio.','Kyoto liegt rechts von Tokio.'] if role=='a' else ['Tokio gehört nach oben links.','Die nächste Reise liegt unter Kyoto.']
        else:
            rewards=[s['reward'] for s in game['stages'][:4]]
            result['labels']=[f'{name} · {digit}' for name,digit in [rewards[1],rewards[0],rewards[2],rewards[3]]] if role=='a' else ['Drei Wochen unterwegs','Unser gemeinsamer Einstieg','Die nächste Reise','Unser Anfang']
            if role=='b': result['rules']=['Zuerst kommt die große Reise.','Danach folgt der Einstieg aus der ersten Etappe.','Die nächste Reise steht vor eurem Anfang.']
        return result
    if stage==3:
        result['rules']=['A und C stehen gleich.','B bleibt ausgeschaltet.'] if role=='a' else ['A und D stehen verschieden.','Genau zwei Schalter sind eingeschaltet.']
        if state['unlocked'] and role=='a': result['fragment']=game['archive']['fragment']
        return result
    return {}
