'use strict';
if(new URLSearchParams(location.hash.slice(1)).has('password'))history.replaceState(null,'',location.pathname+location.search);
const role=location.pathname.split('/')[1];
document.body.className=role==='a'?'romantic':'security';
const $=id=>document.getElementById(id);
let current,source,screen='',selected=null,polling=false,actionQueue=Promise.resolve(),lastVersion=-1,lastStreamUpdate=0,lastRecoveryPoll=0;
let snakeOutcomeAnnounced=false;
const welcomeKey=state=>`cup-welcome-2026-${role}-${state.reset_epoch}`;
const directions={up:'↑',left:'←',down:'↓',right:'→'};
const touchTips=[
 'Smartphone: Tippe Halte, Richtungstasten und Fahrregler an.',
 'Smartphone: Wische über das Spielfeld oder tippe die Richtungstasten an.',
 'Smartphone: Tippe zuerst eine Karte und dann ihren Platz an.',
 'Smartphone: Tippe deine Schalter an und nutze die Eingabefelder im Browser.',
 'Smartphone: Wische über die Ringe oder tippe ▲ und ▼ an.'
];
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,fn,cls='secondary'){const b=el('button',text,cls);b.type='button';b.onclick=fn;return b;}
function card(title,text){const c=el('section',undefined,'puzzle-card');c.append(el('h2',title),el('p',text));return c;}
function connected(){$('connection').textContent='';$('connection').className='online';$('connection').hidden=true;}
async function request(path,data){
 const response=await fetch(`/api/${role}/${path}`,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':current.csrf},body:JSON.stringify(data)});
 const body=await response.json();
 if(!response.ok){
  if(response.status===401){source?.close();$('game').hidden=true;$('connection').hidden=false;$('connection').textContent=body.error;}
  if(response.status===409)refresh();
  throw new Error(body.error||'Bitte versuche es gleich noch einmal.');
 }
 connected();return body;
}
function act(kind,extra={}){
 if(current?.stage===1&&kind==='turn')CupArcade.turn(extra.direction);
 if(kind==='throttle'&&current.stage===0&&current.play.driver===role&&current.play.motion==='stopped'&&current.play.signal!=='green'){
  $('feedback').textContent=current.play.signal==='red'?'Rotes Signal: Bitte das Stellwerk um ein freies Gleis.':'Das Stellwerk muss zuerst die Weiche stellen.';
  return Promise.resolve();
 }
 if(kind==='switch'&&current.stage===3&&!(role==='a'?extra.index<2:extra.index>=2)){
  $('feedback').textContent=`Diesen Hebel bedient ${current.partner}. Du bedienst ${role==='a'?'A und B':'C und D'}.`;
  return Promise.resolve();
 }
 if(current.stage===0&&['set_switch','throttle'].includes(kind))extra={node:current.play.position,...extra};
 const stage=current.stage;
 actionQueue=actionQueue.then(async()=>{try{const data=await request('action',{stage,kind,...extra});$('feedback').textContent='';render(data);}catch(error){$('feedback').textContent=error.message;}});
 return actionQueue;
}
function confirm(extra={}){return act('confirm',extra);}
function makeConfirm(parent){
 const note=el('p','','confirmation-note');note.id='confirmation-note';note.setAttribute('role','status');
 const b=button('Gemeinsam weiter ↗',()=>{
  if(current.stage===0&&!current.play.done){$('feedback').textContent=note.textContent;return;}
  confirm();
 },'primary');b.id='confirm';parent.append(note,b);
}
function render(state){
 $('identity').textContent=state.name;
 if(state.stage===0&&!sessionStorage.getItem(welcomeKey(state))){
  current=state;$('game').hidden=true;$('welcome').hidden=false;connected();
  if(document.activeElement!==$('welcome-start'))$('welcome-title').focus({preventScroll:true});
  return;
 }
 $('welcome').hidden=true;
 if(state.version<lastVersion)return;
 lastVersion=state.version;current=state;document.body.classList.toggle('arcade-mode',!state.complete&&state.stage!==2);
 $('game').hidden=false;
 $('self-name').textContent=state.name;$('peer-name').textContent=state.partner;
 $('self-status').textContent=state.complete||state.solved?'✓ Bestätigt':'In Arbeit';
 $('peer-status').textContent=state.complete||state.peer_solved?'✓ Bestätigt':'In Arbeit';
 $('cooperation').textContent=state.solved?'Dein Beitrag ist bestätigt. Dein Gegenüber bestätigt noch; danach geht es gemeinsam weiter.':state.peer_solved?'Dein Gegenüber hat bestätigt. Wenn ihr fertig seid, bestätige ebenfalls.':'';
 $('steps').replaceChildren(...Array.from({length:state.total},(_,i)=>{const n=el('span',`${String(i+1).padStart(2,'0')} ${i<state.stage?'✓':''}`,i===state.stage?'active':i<state.stage?'done':'');if(i===state.stage)n.setAttribute('aria-current','step');return n;}));
 $('rewards').replaceChildren(...state.rewards.map(([name,value])=>{const n=el('div',undefined,'reward');n.append(el('span',name),el('strong',value));return n;}));
 if(!state.rewards.length)$('rewards').append(el('p','Vier gemeinsame Aufgaben, vier Erinnerungsstücke.'));
 if(state.cup){const winner=state.cup==='tie'?'Geteilter CUP':state.cup===role?`${state.name} hat den CUP gewonnen`:`${state.partner} hat den CUP gewonnen`;$('rewards').append(el('p',`♜ ${winner}`,'cup-badge'));}
 $('hint-section').hidden=state.complete;$('finished').hidden=!state.complete;
 $('touch-help').hidden=state.complete;
 if(!state.complete)$('touch-help').textContent=touchTips[state.stage];
 const nextScreen=state.complete?'done':`${state.stage}:${state.stage===0?state.play.leg:''}`;
 if(screen!==nextScreen){
  const changed=screen!=='';screen=nextScreen;selected=null;CupArcade.destroy();$('feedback').textContent='';$('puzzle').replaceChildren();
  $('chapter').textContent=state.complete?'Euer gemeinsamer Abschluss':`Etappe ${state.stage+1} / ${state.total}`;
  $('title').textContent=state.complete?'Gemeinsam geöffnet.':state.stage_title;
  $('subtitle').textContent=state.complete?'Der CUP hat einen Sieger. Die Box habt ihr gemeinsam geöffnet.':state.subtitle;
  $('intro').textContent=state.complete?'Vier Aufgaben, zwei Perspektiven, ein gemeinsames Ergebnis.':state.intro;
  if(state.complete){$('code').textContent=state.code;$('greeting').textContent=state.greeting;$('postscript').hidden=role!=='b';$('live').textContent='';}
  else [buildTrain,buildSnake,()=>buildBoard(false),buildCircuit,buildLock][state.stage]();
  if(changed){$('title').focus({preventScroll:true});$('title').scrollIntoView({block:'start'});}
 }
 if(state.complete)return;
 $('hints').replaceChildren(...state.hints.map(text=>el('li',text)));
 $('hint').disabled=state.hints.length===3;
 $('hint').textContent=['Ersten Hinweis öffnen','Zweiten Hinweis öffnen','Dritten Hinweis öffnen','Alle drei Hinweise geöffnet'][state.hints.length];
 $('live').textContent=state.play.last_action||state.play.last||'';
 [updateTrain,updateSnake,updateBoard,updateCircuit,updateLock][state.stage]();
 const c=$('confirm');if(c){c.disabled=state.solved||(state.stage!==0&&!canConfirm(state));c.textContent=state.solved?'Dein Beitrag ist bestätigt ✓':'Gemeinsam weiter ↗';
  const note=$('confirmation-note');if(note){
   if(state.stage===0&&!state.play.done){
    const driver=state.play.driver===role?state.name:state.partner;
    note.textContent=`Noch ist die Fahrt nicht abgeschlossen. ${driver} fährt mit Gas und Bremse von ${state.play.stops[state.play.position]} nach ${state.play.stops[state.play.goal]}. ${state.play.leg===0?'Danach tauscht ihr die Rollen und fahrt zurück nach Weißenhorn.':'Danach könnt ihr beide „Gemeinsam weiter“ bestätigen.'} Das Stellwerk muss vor jedem Abschnitt die Weiche stellen.`;
   }else note.textContent=canConfirm(state)?'Aufgabe geschafft. Bestätigt jetzt beide „Gemeinsam weiter“.':'Löst zuerst die gemeinsame Aufgabe. Danach bestätigt ihr beide.';
  }}
}
function canConfirm(s){if(s.stage===0)return s.play.done;if(s.stage===1)return s.play.phase==='passport'&&s.play.passport.every(Boolean);if(s.stage===2||s.stage===4)return s.play.matched.every(Boolean);return false;}
function buildDirections(parent,kind){const box=el('div',undefined,'direction-pad');for(const name of ['up','left','down','right']){const b=button(directions[name],()=>act(kind,{direction:name}));b.id='dir-'+name;b.setAttribute('aria-label',({up:'Nach oben',down:'Nach unten',left:'Nach links',right:'Nach rechts'})[name]);b.classList.add(name);box.append(b);}parent.append(box);}
function buildTrain(){
 const p=current.play,driver=p.driver===role;
 $('intro').textContent=driver?`Du bedienst Gas und Bremse. ${current.partner} stellt die Weiche. Nenne die Sperren und fahre erst bei grünem Signal.`:`Du stellst die Weiche am aktuellen Halt. ${current.partner} bedient Gas und Bremse und sieht die Sperren. Frage nach einem freien Gleis und wähle dann die Richtung.`;
 const c=el('section',undefined,'arcade-card');
 const hud=el('div',undefined,'train-hud');hud.id='train-position';c.append(hud);
 const viewport=el('div',undefined,'arcade-viewport');viewport.id='train-stage';viewport.setAttribute('role','img');viewport.setAttribute('aria-label',driver?'CUP Express Führerstand mit Signal und Fahrregler':'Stellwerk mit interaktiven Weichen am aktuellen Halt');c.append(viewport);
 const note=el('p','','blocked-note');note.id='blocked';c.append(note);
 if(driver){
  const controls=el('div',undefined,'drive-controls');const gas=button('▶ Gas geben',()=>act('throttle'),'secondary');gas.id='throttle';const brake=button('■ Bremsen',()=>act('brake'),'secondary');brake.id='brake';controls.append(gas,brake);c.append(controls);
 }else buildDirections(c,'set_switch');
 $('puzzle').append(c);CupArcade.mount('train-stage','train',role,act);makeConfirm($('puzzle'));
}
function updateTrain(){
 const p=current.play,driver=p.driver===role,labels={up:'oben',down:'unten',left:'links',right:'rechts'};
 $('train-position').textContent=p.done?'✓ TEAMSTRECKE GESCHAFFT':`ABSCHNITT ${p.leg+1}/2 · ${p.stops[p.position]} → ${p.stops[p.goal]}`;
 if(driver){
  const signal=p.motion==='paused'?'Gebremst. Gib Gas, um die Fahrt fortzusetzen.':p.motion==='moving'?'Der Zug fährt und hält am nächsten Halt automatisch.':p.signal==='unset'?`${current.partner} stellt zuerst die Weiche.`:p.signal==='red'?'Rotes Signal: Das gewählte Gleis ist gesperrt. Bitte um eine andere Weichenstellung.':'Grünes Signal. Du kannst Gas geben.';
  $('blocked').textContent=p.done?'Beide Fahrten geschafft.':`Gesperrt: ${p.blocked.map(d=>labels[d]).join(', ')}. ${signal}`;
  $('throttle').disabled=p.done||p.motion==='moving';$('throttle').textContent=p.motion==='paused'?'▶ Weiterfahren':'▶ Gas geben';$('brake').disabled=p.done||p.motion!=='moving';
 }else{
  $('blocked').textContent=p.done?'Beide Fahrten geschafft.':p.motion!=='stopped'?'Die Weiche ist während der Fahrt verriegelt. Warte bis zum nächsten Halt.':p.switch_direction?`Weiche nach ${labels[p.switch_direction]} gestellt. ${current.partner} prüft das Signal und gibt Gas.`:'Tippe einen benachbarten Halt an oder stelle die Weiche mit den Pfeilen.';
  for(const d of Object.keys(directions)){const b=$('dir-'+d);b.disabled=p.done||p.motion!=='stopped'||!p.tracks.includes(d);b.classList.toggle('switch-selected',p.switch_direction===d);b.setAttribute('aria-label',`Weiche nach ${labels[d]} stellen`);}
 }
 CupArcade.update(current);
}
function buildSnake(){
 snakeOutcomeAnnounced=false;
 const c=el('section',undefined,'snake-card');
 const challenge=el('p',undefined,'snake-challenge');challenge.id='snake-challenge';challenge.textContent='🏆 Japan-CUP: Drei Minuten, zwei Schlangen, ein CUP. Wer mehr Reisestationen sammelt, gewinnt. Danach bringt ihr den Reisepass gemeinsam ins Ziel.';c.append(challenge);
 const score=el('div',undefined,'scoreboard');score.id='scoreboard';c.append(score);
 const info=el('p');info.id='snake-info';c.append(info);
 const result=el('section',undefined,'snake-result');result.id='snake-result';result.hidden=true;result.setAttribute('role','status');result.setAttribute('aria-live','assertive');
 const trophy=el('span','🏆','snake-trophy');trophy.setAttribute('aria-hidden','true');
 const heading=el('h2');heading.id='snake-result-heading';const finalScore=el('p');finalScore.id='snake-result-score';
 result.append(trophy,heading,finalScore,el('p','Der CUP ist entschieden. Den Reisepass bringt ihr jetzt nur zusammen ins Ziel.','snake-result-next'));
 const viewport=el('div',undefined,'arcade-viewport');viewport.id='snake';viewport.setAttribute('role','img');viewport.setAttribute('aria-label','Japan Snake Spielfeld. Pfeile, WASD oder Wischen.');c.append(viewport);
 const stage=el('div',undefined,'snake-stage');c.replaceChild(stage,viewport);stage.append(viewport,result);
 buildDirections(c,'turn');const controls=el('div',undefined,'game-buttons');
 for(const [id,text,fn] of [['practice','Ohne Punkte üben',()=>act('practice')],['ready','Ich bin bereit',()=>act('ready')],['send','Stempel weiterschicken',()=>act('send')]]){const b=button(text,fn);b.id=id;controls.append(b);}c.append(controls);
 const list=el('div',undefined,'passport');list.id='passport';c.append(el('h2','Euer gemeinsamer Reisepass'),list);
 const repair=el('section',undefined,'passport-repair');repair.id='repair';repair.append(el('p','Ergänzt die fehlenden Stationen in eurer Reiseroute. Abwechselnd gehört ein Halt der einen oder der anderen Seite. Helft euch mit der Reihenfolge.'));
 const next=el('p');next.id='next-stamp';repair.append(next);const choices=el('div',undefined,'station-choices');choices.id='station-choices';
 current.play.route.map((name,i)=>[name,i]).sort((a,b)=>a[0].localeCompare(b[0])).forEach(([name,i])=>{const b=button(name,()=>act('stamp',{station:i}));b.dataset.station=i;choices.append(b);});repair.append(choices);c.append(repair);$('puzzle').append(c);CupArcade.mount('snake','snake',role,act);makeConfirm($('puzzle'));
}
function updateSnake(){
 const p=current.play,active=p.phase==='race'||p.practice;
 const timer=p.phase==='countdown'?`Start in ${p.countdown}`:p.phase==='race'?`${Math.floor(p.remaining/60)}:${String(p.remaining%60).padStart(2,'0')}`:p.phase==='passport'?'Rennen beendet':'Proberunde';
 const ownScore=el('span',`${current.name} · ${p.score}`),peerScore=el('span',`${current.partner} · ${p.peer_score}`);
 if(p.phase==='passport'){
  ownScore.classList.toggle('snake-score-winner',p.winner===role||p.winner==='tie');
  peerScore.classList.toggle('snake-score-winner',p.winner!==role);
  $('snake-result-heading').textContent=p.winner==='tie'?`${current.name} und ${current.partner} teilen sich den Japan-CUP!`:`${p.winner===role?current.name:current.partner} gewinnt den Japan-CUP!`;
  $('snake-result-score').textContent=`Endstand: ${current.name} ${p.score} : ${p.peer_score} ${current.partner}`;
  $('snake-result').hidden=false;
  if(!snakeOutcomeAnnounced){$('snake-result').classList.add('snake-result-enter');snakeOutcomeAnnounced=true;}
 }
 $('scoreboard').replaceChildren(ownScore,el('strong',timer),peerScore);
 $('snake-info').textContent=p.phase==='passport'?(p.winner==='tie'?'Gleichstand. Ihr teilt euch den CUP.':`${p.winner===role?current.name:current.partner} hat den CUP gewonnen. Jetzt macht ihr den Reisepass gemeinsam voll.`):p.paused?'Die Uhr wartet: Eine Seite hat gerade keine Verbindung.':p.phase==='countdown'?'Beide sind bereit. Gleich geht es los.':p.phase==='warmup'?(p.ready[role]?`Du bist bereit. Warte auf ${current.partner}.`:'Übe zuerst die Steuerung. Danach bestätigt ihr beide eure Bereitschaft.'):`Nächster Halt: ${p.station} · Stempel für ${p.target_owner===role?'dich':current.partner}`;
 CupArcade.update(current);
 for(const d of Object.keys(directions))$('dir-'+d).disabled=!active;
 $('practice').hidden=p.phase!=='warmup';$('practice').disabled=p.ready[role]||p.practice;
 $('ready').hidden=p.phase!=='warmup';$('ready').disabled=p.ready[role];
 $('send').hidden=!['race','passport'].includes(p.phase);$('send').disabled=!p.held;$('send').textContent=`${p.held} Stempel weiterschicken`;
 $('passport').replaceChildren(...p.route.map((name,i)=>el('span',`${p.passport[i]?'✓':'○'} ${name}`,p.passport[i]?'stamped':'')));
 $('repair').hidden=p.phase!=='passport'||p.passport.every(Boolean);
 $('next-stamp').textContent=p.stamp_role===role?'Du ergänzt den nächsten fehlenden Halt.':`${current.partner} ergänzt den nächsten Halt. Hilf mit der Reihenfolge.`;
 if(current.hints.length===3&&p.missing!==null)$('next-stamp').textContent+=` Nächster fehlender Halt: ${p.route[p.missing]}.`;
 for(const b of $('station-choices').children)b.disabled=p.stamp_role!==role||p.passport[Number(b.dataset.station)];
}
function buildBoard(lock){
 const c=card(lock?'Vier Ringe für eure Box':role==='a'?'Deine Bildkarten':'Deine Beschriftungen',lock?'Wähle eine Karte und dann ihren Platz. Jede Änderung erscheint auch auf der anderen Seite.':'Wähle eine Karte und dann einen Platz im Album. Dein Gegenüber ordnet seine eigene Hälfte.');
 if(current.play.rules)current.play.rules.forEach(text=>c.append(el('p',text,'rule')));
 const choices=el('div',undefined,'tile-choices');choices.id='tile-choices';
 current.play.labels.forEach((name,i)=>{const b=button(name,()=>{selected=i;for(const child of choices.children)child.classList.toggle('selected',Number(child.dataset.item)===i);$('board-instruction').textContent='Wähle jetzt den Platz für diese Karte.';},'tile-choice');b.dataset.item=i;b.setAttribute('aria-pressed','false');if(!lock&&role==='a')b.dataset.picture=['city','temple','island','sun'][i];choices.append(b);});c.append(choices);
 const instruction=el('p','Wähle zuerst eine Karte.','board-instruction');instruction.id='board-instruction';c.append(instruction);
 const slots=el('div',undefined,lock?'lock-slots':'album-slots');slots.id='slots';
 for(let i=0;i<4;i++){const b=button('',()=>{if(selected===null){$('feedback').textContent='Wähle zuerst eine Karte.';return;}act('place',{item:selected,position:i});},'board-slot');b.dataset.position=i;slots.append(b);}c.append(slots);
 c.append(el('p','Die kleinen Markierungen zeigen Bewegungen auf der anderen Seite. Inhalte bleiben getrennt.','fineprint'));const peer=el('div',undefined,'peer-preview');peer.id='peer-preview';c.append(peer);$('puzzle').append(c);makeConfirm($('puzzle'));
}
function updateBoard(){const p=current.play;for(let i=0;i<4;i++){const b=$('slots').children[i];const label=p.labels[p.order[i]];b.replaceChildren(el('small',current.stage===4?`Ring ${i+1}`:['Oben links','Oben rechts','Unten links','Unten rechts'][i]),el('span',label),el('small',p.matched[i]?'✓ Beide Seiten passen':'Noch nicht eingerastet'));b.classList.toggle('matched',p.matched[i]);b.setAttribute('aria-label',`Platz ${i+1}: ${label}`);}
 $('peer-preview').replaceChildren(...p.peer_positions.map((position,i)=>el('span',`● ${i+1} → ${position+1}`)));
 for(const b of $('tile-choices').children)b.setAttribute('aria-pressed',String(Number(b.dataset.item)===selected));
}
function buildLock(){
 $('intro').textContent=role==='a'?`Du bedienst die Zahlenringe. ${current.partner} ordnet die Kapitel. Sprecht über eure Erinnerungsstücke und dreht beide die Ringe in dieselbe Reihenfolge.`:`Du bedienst die Kapitelringe. ${current.partner} besitzt die Zahlen dazu. Nutze deine Reihenfolge-Hinweise, um eure beiden Boxhälften abzustimmen.`;
 const c=el('section',undefined,'arcade-card');const viewport=el('div',undefined,'arcade-viewport');viewport.id='lock-stage';viewport.setAttribute('role','img');viewport.setAttribute('aria-label','Vier interaktive Schlossringe. Mit Pfeilen drehen oder über die Ringe wischen.');c.append(viewport);$('puzzle').append(c);
 const notes=card(role==='a'?'Deine Erinnerungsstücke':'Dein Plan für die Box','Drehe jeden Ring mit ▲ und ▼ oder wische über den Ring im Spielfeld. Jede Person bedient ihre eigene Boxhälfte.');
 if(current.play.rules)for(const rule of current.play.rules)notes.append(el('p',rule,'rule'));
 const collection=el('div',undefined,'lock-collection');for(const label of current.play.labels)collection.append(el('span',label));notes.append(collection);
 const controls=el('div',undefined,'ring-controls');for(let i=0;i<4;i++){
  const group=el('div',undefined,'ring-control');const text=el('p');text.id='ring-label-'+i;
  const up=button('▲',()=>act('rotate',{position:i,step:1}),'secondary');up.dataset.ring=i;up.dataset.step=1;up.setAttribute('aria-label',`Ring ${i+1} vorwärts drehen`);
  const down=button('▼',()=>act('rotate',{position:i,step:-1}),'secondary');down.dataset.ring=i;down.dataset.step=-1;down.setAttribute('aria-label',`Ring ${i+1} rückwärts drehen`);group.append(text,up,down);controls.append(group);
 }notes.append(controls);$('puzzle').append(notes);CupArcade.mount('lock-stage','lock',role,act);makeConfirm($('puzzle'));
}
function updateLock(){const p=current.play;for(let i=0;i<4;i++)$('ring-label-'+i).textContent=`Ring ${i+1}: ${p.labels[p.order[i]]}${p.matched[i]?' ✓':''}`;CupArcade.update(current);}
function buildCircuit(){
 $('intro').textContent=`Bringt gemeinsam Strom ins CUP Lab. Du bedienst ${role==='a'?'A und B':'C und D'}; ${current.partner} bedient die andere Hälfte. Nur zusammen kennt ihr alle Bedingungen.`;
 const c=el('section',undefined,'arcade-card');const viewport=el('div',undefined,'arcade-viewport');viewport.id='circuit-stage';viewport.setAttribute('role','img');viewport.setAttribute('aria-label','Interaktives Schaltpult mit vier Hebeln und gemeinsamen Stromleitungen');c.append(viewport);$('puzzle').append(c);
 const notes=card('Deine Bedingungen','Teilt die Hinweise, stellt eure Schalter ein und prüft die Schaltung anschließend beide.');
 current.play.rules.forEach(text=>notes.append(el('p',text,'rule')));
 const board=el('div',undefined,'switch-board');
 for(let i=0;i<4;i++){const b=button('',()=>act('switch',{index:i}),'switch');b.dataset.index=i;board.append(b);}notes.append(board);
 const check=button('Schaltung prüfen',()=>act('check'),'primary');check.id='check';notes.append(check);$('puzzle').append(notes);CupArcade.mount('circuit-stage','circuit',role,act);
 const archive=el('section',undefined,'puzzle-card');archive.id='archive-panel';
 if(role==='a'){
  archive.append(el('h2','Dein Schlüsselteil'),el('p',`Nenne ${current.partner} diesen Schlüssel oder schicke ihn im Chat. Er ist für diese Spielrunde bestimmt.`));
  const fragment=el('code');fragment.id='fragment';archive.append(fragment);
  const copy=button('Schlüssel kopieren',async()=>{try{await navigator.clipboard.writeText(current.play.fragment);$('feedback').textContent='Schlüssel kopiert.';}catch{$('feedback').textContent='Markiere den Schlüssel und kopiere ihn in euren Chat.';}});archive.append(copy);
  const form=el('form');form.id='word-form';const label=el('label','Welches Prüfwort hat dein Gegenüber ermittelt?');label.htmlFor='word';const input=el('input');input.id='word';input.maxLength=8;input.required=true;input.autocomplete='off';input.spellcheck=false;const submit=el('button','Prüfwort bestätigen ↗','primary');submit.type='submit';submit.id='receipt-submit';form.append(label,input,submit);form.onsubmit=e=>{e.preventDefault();confirm({word:input.value});};archive.append(form);
 }else{
  archive.append(el('h2','Das verschlüsselte Archiv'),el('p','Öffne die Datei in einem eigenen Werkzeug oder nutze den Helfer unten. Der Helfer zeigt nur den berechneten Wert und das Prüfwort, niemals das entschlüsselte Datum.'));
  const download=el('a','Archiv im Browser öffnen');download.href='/api/b/archive';download.target='_blank';download.rel='noopener';archive.append(download);
  archive.append(el('p','Dateiformat: Hex-Geheimtext XOR SHA-256(Schlüsselteil:Salz). Die Datei beschreibt die Berechnung und die Prüfung.','fineprint'));
  const form=el('form');const label=el('label','Schlüsselteil von deiner Mitspielerin');label.htmlFor='archive-key';const input=el('input');input.id='archive-key';input.autocomplete='off';input.spellcheck=false;input.required=true;const submit=el('button','Archiv prüfen','secondary');submit.type='submit';form.append(label,input,submit);
  form.onsubmit=async e=>{e.preventDefault();archiveProof=null;$('receipt-submit').disabled=true;$('archive-result').textContent='';try{await decrypt(input.value.trim());}catch{$('feedback').textContent='Die Datei ließ sich mit diesem Schlüssel nicht prüfen. Vergleicht den Schlüssel und versucht es erneut.';}};archive.append(form);
  const result=el('p');result.id='archive-result';result.setAttribute('role','status');archive.append(result);
  const confirmButton=button('Ergebnis bestätigen ↗',()=>confirm(archiveProof),'primary');confirmButton.id='receipt-submit';confirmButton.disabled=true;archive.append(confirmButton);
 }
 $('puzzle').append(archive);
}
let archiveProof=null;
async function digest(value){return new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));}
function hex(bytes){return Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join('');}
async function decrypt(fragment){
 const archive=await request('archive');const key=await digest(fragment+':'+archive.salt);
 const cipher=archive.cipher_hex.match(/../g).map(x=>parseInt(x,16));
 const bytes=cipher.map((x,i)=>x^key[i]);
 if(!bytes.every(x=>x>=48&&x<=57)||bytes.length!==8)throw new Error('format');
 const secret=String.fromCharCode(...bytes);const day=Number(secret.slice(0,2)),month=Number(secret.slice(2,4));
 if(day<1||day>31||month<1||month>12)throw new Error('format');
 const receipt=hex(await digest(archive.salt+':'+secret));
 archiveProof={value:Math.abs(day-month)%10,receipt};
 $('archive-result').textContent=`Berechneter Wert: ${archiveProof.value} · Prüfwort: ${receipt.slice(0,8).toUpperCase()}. Teile das Prüfwort mit deiner Mitspielerin.`;
 $('receipt-submit').disabled=false;
}
function updateCircuit(){const p=current.play;CupArcade.update(current);for(const b of document.querySelectorAll('.switch')){const i=Number(b.dataset.index),own=role==='a'?i<2:i>=2;b.textContent=`${String.fromCharCode(65+i)} · ${p.switches[i]?'Ein':'Aus'}`;b.classList.toggle('on',p.switches[i]);b.disabled=!own||p.unlocked;b.setAttribute('aria-pressed',String(p.switches[i]));}
 $('check').disabled=p.unlocked||p.armed[role];$('check').textContent=p.unlocked?'Schaltung gemeinsam geprüft ✓':p.armed[role]?'Deine Prüfung ist bestätigt ✓':'Schaltung prüfen';
 $('archive-panel').hidden=!p.unlocked;
 if(p.unlocked&&role==='a')$('fragment').textContent=p.fragment;
 if(current.solved){$('receipt-submit').disabled=true;$('receipt-submit').textContent='Dein Beitrag ist bestätigt ✓';}
}
$('welcome-start').onclick=()=>{sessionStorage.setItem(welcomeKey(current),'seen');$('welcome').hidden=true;render(current);};
$('hint').onclick=async()=>{try{render(await request('hint',{stage:current.stage}));}catch(error){$('feedback').textContent=error.message;}};
$('logout').onclick=async()=>{try{await request('logout',{});sessionStorage.removeItem(welcomeKey(current));source?.close();location.replace('/');}catch(error){$('feedback').textContent=error.message;}};
async function refresh(){if(polling)return;polling=true;try{render(await request('state'));}catch(error){$('connection').textContent=error.message||'Verbindung unterbrochen.';$('connection').className='offline';$('connection').hidden=false;}finally{polling=false;}}
function listen(){source=new EventSource(`/api/${role}/events`);source.onopen=()=>{lastStreamUpdate=Date.now();};source.onmessage=e=>{lastStreamUpdate=Date.now();connected();render(JSON.parse(e.data));};source.addEventListener('expired',()=>{source.close();refresh();});source.onerror=()=>{lastStreamUpdate=0;$('connection').textContent='Verbindung wird erneuert …';$('connection').className='offline';$('connection').hidden=false;};}
refresh().then(()=>{if(current)listen();});
setInterval(()=>{if(!current||current.complete||current.stage>=2||document.hidden)return;
 const now=Date.now(),streamOpen=source?.readyState===EventSource.OPEN;
 if(streamOpen&&now-lastStreamUpdate<1200)return;
 if(streamOpen&&now-lastRecoveryPoll<1000)return;
 lastRecoveryPoll=now;refresh();
},240);
setInterval(()=>{if(current?.stage>=2&&!document.hidden)refresh();},5000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});window.addEventListener('online',refresh);
window.addEventListener('keydown',e=>{
 if(!current||!$('welcome').hidden||current.complete||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||e.ctrlKey||e.metaKey||e.altKey)return;
 const d={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',w:'up',a:'left',s:'down',d:'right'}[e.key.length===1?e.key.toLowerCase():e.key];
 if(current.stage===0){
  if(current.play.driver===role&&[' ','b','B'].includes(e.key)&&(e.key!==' '||e.target.tagName!=='BUTTON')){
   e.preventDefault();if(e.repeat)return;act(e.key===' '?'throttle':'brake');return;
  }
  if(d){e.preventDefault();if(e.repeat)return;if(current.play.driver===role){$('feedback').textContent='Dein Gegenüber stellt die Weiche. Du gibst mit Leertaste Gas und bremst mit B.';return;}if(!current.play.done&&current.play.motion==='stopped'&&current.play.tracks.includes(d))act('set_switch',{direction:d});}
 }else if(current.stage===1&&d&&(current.play.phase==='race'||current.play.practice)){e.preventDefault();if(!e.repeat)act('turn',{direction:d});}
});
window.addEventListener('offline',()=>{$('connection').textContent='Du bist offline.';$('connection').className='offline';$('connection').hidden=false;});
