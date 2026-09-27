'use strict';
// Phaser 3 scenes display server-authoritative state; they never award points.
window.CupArcade=(()=>{
 let game,scene,pending,mode,send,own;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const colors={bg:0x102b32,rail:0x547279,mint:0x83e3c5,gold:0xffcf73,red:0xff827b,white:0xf5f4e9};
 const pos=i=>({x:115+(i%3)*185,y:130+Math.floor(i/3)*145});
 function mount(parent,type,role,onAction){
  destroy();mode=type;own=role;send=onAction;
  class CupScene extends Phaser.Scene{
   create(){
    scene=this;this.board=this.add.graphics();this.ink=[];this.lastPosition=null;this.lastBody='';
    this.sky=this.add.graphics();this.sky.fillStyle(0x163a43);this.sky.fillCircle(590,70,115);this.sky.fillCircle(0,470,145);this.sky.setDepth(-1);
    this.train=this.add.container(0,0).setDepth(5);const sprite=this.add.graphics();
    sprite.fillStyle(0x091e25,.3);sprite.fillRoundedRect(-35,-19,74,45,12);
    sprite.fillStyle(colors.white);sprite.fillRoundedRect(-34,-27,68,40,12);sprite.fillStyle(colors.mint);sprite.fillRoundedRect(-30,-25,60,12,5);
    sprite.fillStyle(0x244651);sprite.fillRoundedRect(-19,-10,13,14,3);sprite.fillRoundedRect(3,-10,13,14,3);
    sprite.fillStyle(colors.gold);sprite.fillCircle(-29,5,3);sprite.fillCircle(29,5,3);sprite.fillStyle(0x071e28);sprite.fillCircle(-20,16,6);sprite.fillCircle(20,16,6);
    this.train.add(sprite);this.badge=this.add.text(300,38,'',{fontFamily:'Arial',fontSize:'15px',color:'#83e3c5',fontStyle:'bold'}).setOrigin(.5);
    this.message=this.add.text(300,502,'',{fontFamily:'Arial',fontSize:'16px',color:'#f5f4e9',align:'center',wordWrap:{width:535}}).setOrigin(.5);
    if(mode!=='train')this.train.setVisible(false);this.levers=[];this.ringTexts=[];this.lastOrder=null;
    if(mode==='circuit')for(let i=0;i<4;i++){const n=this.add.graphics();n.fillStyle(colors.white);n.fillRoundedRect(-26,-13,52,26,10);n.fillStyle(colors.mint);n.fillCircle(0,0,7);this.levers.push(n.setDepth(4));}
    if(mode==='lock')for(let i=0;i<4;i++)this.ringTexts.push(this.add.text(120+i*120,275,'',{fontFamily:'Arial',fontSize:'36px',fontStyle:'bold',color:'#f5f4e9'}).setOrigin(.5).setDepth(4));
    this.input.on('pointerdown',pointer=>{
     if(mode==='circuit'&&pending&&!pending.play.unlocked){
      for(let i=0;i<4;i++){const x=180+(i%2)*240,y=180+Math.floor(i/2)*180;if(Math.abs(pointer.x-x)<80&&Math.abs(pointer.y-y)<70)send('switch',{index:i});}
     }
     if(mode==='lock'&&pending){
      const i=Math.round((pointer.x-120)/120);
      if(i>=0&&i<4&&Math.abs(pointer.x-(120+i*120))<50){if(pointer.y>140&&pointer.y<218)send('rotate',{position:i,step:1});else if(pointer.y>328&&pointer.y<405)send('rotate',{position:i,step:-1});}
     }
     if(mode==='train'&&pending&&!pending.play.done&&pending.play.driver!==own&&pending.play.motion==='stopped'){
      const here=pending.play.position;
      for(let i=0;i<9;i++){const p=pos(i);if(Phaser.Math.Distance.Between(pointer.x,pointer.y,p.x,p.y)<39){const dx=i%3-here%3,dy=Math.floor(i/3)-Math.floor(here/3);if(Math.abs(dx)+Math.abs(dy)===1)send('set_switch',{direction:dx===1?'right':dx===-1?'left':dy===1?'down':'up'});}}
     }
     if(mode==='train'&&pending&&!pending.play.done&&pending.play.driver===own){
      if(pointer.y>380&&pointer.y<450&&pointer.x>120&&pointer.x<290&&pending.play.motion!=='moving')send('throttle');
      if(pointer.y>380&&pointer.y<450&&pointer.x>310&&pointer.x<480&&pending.play.motion==='moving')send('brake');
     }
    });
    let start;this.input.on('pointerdown',p=>{start={x:p.x,y:p.y}});
    this.input.on('pointerup',p=>{if(!start)return;const dx=p.x-start.x,dy=p.y-start.y;const origin=start;start=null;
     if(mode==='lock'&&origin.y>=218&&origin.y<=328&&Math.abs(dy)>24){const i=Math.round((origin.x-120)/120);if(i>=0&&i<4)send('rotate',{position:i,step:dy<0?1:-1});return;}
     if(mode!=='snake'||Math.max(Math.abs(dx),Math.abs(dy))<22)return;send('turn',{direction:Math.abs(dx)>Math.abs(dy)?dx>0?'right':'left':dy>0?'down':'up'});});
    if(pending)this.paint(pending);
   }
   text(x,y,t,size=16,color='#c2d6d6'){const n=this.add.text(x,y,t,{fontFamily:'Arial',fontSize:size+'px',color,fontStyle:'bold'}).setOrigin(.5);this.ink.push(n);return n;}
   paint(s){
    const p=s.play,g=this.board;g.clear();this.ink.forEach(n=>n.destroy());this.ink=[];
    if(mode==='train'){
     const driver=p.driver===own;
     this.badge.setText(p.done?'TEAMSTRECKE GESCHAFFT':`CUP EXPRESS · ABSCHNITT ${p.leg+1}/2 · ${driver?'FÜHRERSTAND':'STELLWERK'}`);
     if(!driver){
      g.lineStyle(10,0x294e57);for(let i=0;i<9;i++){const a=pos(i);for(const next of [i%3<2?i+1:-1,i<6?i+3:-1])if(next>=0){const b=pos(next);g.lineBetween(a.x,a.y,b.x,b.y);}}
      g.lineStyle(2,colors.rail);for(let i=0;i<9;i++){const a=pos(i);for(const next of [i%3<2?i+1:-1,i<6?i+3:-1])if(next>=0){const b=pos(next);g.lineBetween(a.x,a.y,b.x,b.y);}}
      let switchTarget=null;if(p.switch_direction){const offsets={up:-3,down:3,left:-1,right:1};switchTarget=p.position+offsets[p.switch_direction];const a=pos(p.position),b=pos(switchTarget);g.lineStyle(7,colors.gold);g.lineBetween(a.x,a.y,b.x,b.y);}
      for(let i=0;i<9;i++){const a=pos(i),adjacent=Math.abs(i%3-p.position%3)+Math.abs(Math.floor(i/3)-Math.floor(p.position/3))===1;
       g.fillStyle(i===p.goal?colors.gold:i===switchTarget?0x47725e:0x244a55);g.fillCircle(a.x,a.y,29);g.lineStyle(adjacent&&p.motion==='stopped'?3:2,adjacent&&p.motion==='stopped'?colors.mint:colors.rail);g.strokeCircle(a.x,a.y,35);this.text(a.x,a.y,String.fromCharCode(65+i),22,i===p.goal?'#102b32':'#f5f4e9');}
      const from=pos(p.position),to=p.travel?pos(p.travel.target):from,t=p.travel_progress||0;const target={x:from.x+(to.x-from.x)*t,y:from.y+(to.y-from.y)*t-12};
      this.tweens.killTweensOf(this.train);if(this.lastPosition===null)this.train.setPosition(target.x,target.y);else this.tweens.add({targets:this.train,x:target.x,y:target.y,duration:reduced?0:200,ease:'Linear'});this.lastPosition=p.position;
      this.message.setText(p.done?'Beide Fahrten geschafft. Bestätigt euren Teambeitrag.':p.motion==='moving'?'Der Zug fährt. Die Weiche bleibt verriegelt.':p.motion==='paused'?'Der Fahrer hat gebremst. Die Weiche bleibt verriegelt.':'Tippe den nächsten benachbarten Halt an, um die Weiche zu stellen.');
     }else{
      const cx=300,cy=250;g.fillStyle(0x183f49);g.fillRoundedRect(95,102,410,225,28);g.lineStyle(8,0x355b64);g.lineBetween(220,120,280,275);g.lineBetween(380,120,320,275);
      this.train.setPosition(cx,cy);this.lastPosition=p.position;
      const signal=p.motion==='moving'||p.motion==='paused'?'green':p.signal;const color=signal==='green'?colors.mint:signal==='red'?colors.red:colors.gold;
      g.fillStyle(0x091e25);g.fillRoundedRect(250,62,100,88,19);g.fillStyle(color);g.fillCircle(300,105,25);
      this.text(300,175,p.motion==='moving'?'ZUG FÄHRT':p.motion==='paused'?'GEBREMST':signal==='green'?'FAHRT FREI':signal==='red'?'GLEIS GESPERRT':'WEICHE FEHLT',20,signal==='red'?'#ff827b':'#f5f4e9');
      this.text(300,300,`HALT ${String.fromCharCode(65+p.position)}`,19,'#ffcf73');
      const labels={up:'OBEN',down:'UNTEN',left:'LINKS',right:'RECHTS'};this.text(300,346,`WEICHE: ${p.switch_direction?labels[p.switch_direction]:'NOCH NICHT GESTELLT'}`,14);
      g.fillStyle(p.motion==='moving'?0x244a55:0x21584e);g.fillRoundedRect(120,382,170,60,15);this.text(205,412,p.motion==='paused'?'▶ WEITER':'▶ GAS',21,'#83e3c5');
      g.fillStyle(p.motion==='moving'?0x7a663f:0x244a55);g.fillRoundedRect(310,382,170,60,15);this.text(395,412,'■ BREMSE',19,'#ffcf73');
      this.message.setText(p.done?'Ziel erreicht. Bestätigt jetzt beide.':'Leertaste: Gas · B: Bremse · oder tippe auf die Fahrregler.');
     }
    }else if(mode==='circuit'){
     this.badge.setText(p.unlocked?'ARCHIV MIT TEAMSTROM GEÖFFNET':'CUP LAB  ·  ZWEI HÄNDE, EIN STROMKREIS');
     g.fillStyle(0x173941);g.fillRoundedRect(54,85,492,370,25);
     g.lineStyle(7,p.unlocked?colors.mint:0x355b64);g.lineBetween(300,108,300,435);
     for(let i=0;i<4;i++){
      const x=180+(i%2)*240,y=180+Math.floor(i/2)*180,on=p.switches[i],mine=own==='a'?i<2:i>=2;
      g.lineStyle(5,on?colors.mint:0x355b64);g.lineBetween(x,y,300,y);
      g.fillStyle(mine?0x234f59:0x1a343e);g.fillRoundedRect(x-78,y-66,156,132,18);g.lineStyle(2,mine?colors.gold:colors.rail);g.strokeRoundedRect(x-78,y-66,156,132,18);
      this.text(x,y-44,`${String.fromCharCode(65+i)} · ${mine?'DEIN SCHALTER':'GEGENÜBER'}`,12,mine?'#ffcf73':'#c2d6d6');
      g.fillStyle(0x0d252c);g.fillRoundedRect(x-30,y-17,60,58,12);
      const lever=this.levers[i],targetY=y+(on?-1:23);if(lever.x!==x){lever.setPosition(x,targetY);lever.on=on;}else if(lever.on!==on){this.tweens.killTweensOf(lever);this.tweens.add({targets:lever,y:targetY,duration:reduced?0:180,ease:'Back.easeOut'});lever.on=on;}
      this.text(x,y+53,on?'EIN':'AUS',13,on?'#83e3c5':'#c2d6d6');
     }
     const checked=Object.values(p.armed).filter(Boolean).length;this.text(300,470,p.unlocked?'✓ BEIDE PRÜFUNGEN BESTANDEN':`TEAMPRÜFUNG ${checked}/2`,15,p.unlocked?'#83e3c5':'#ffcf73');
     this.message.setText(p.unlocked?'Das Archiv wartet unten. Tauscht Schlüssel und Prüfwort.':'Tippe deine Schalter an. Die andere Hälfte bedient dein Gegenüber.');
    }else if(mode==='lock'){
     this.badge.setText('C ∪ P  ·  DIE GEMEINSAME SCHLÜSSELBOX');
     g.lineStyle(18,0xb7995d);g.strokeRoundedRect(225,70,150,145,50);
     g.fillStyle(0x23454f);g.fillRoundedRect(45,146,510,282,28);g.lineStyle(3,0xb7995d);g.strokeRoundedRect(45,146,510,282,28);
     for(let i=0;i<4;i++){
      const x=120+i*120,item=p.order[i],matched=p.matched[i];
      g.fillStyle(0x0c242d);g.fillRoundedRect(x-47,194,94,169,13);g.lineStyle(2,matched?colors.mint:colors.rail);g.strokeRoundedRect(x-47,194,94,169,13);
      this.text(x,178,'▲',24,'#ffcf73');this.text(x,387,'▼',24,'#ffcf73');
      const previous=(item+3)%4,next=(item+1)%4;
      const value=id=>own==='a'?p.labels[id].split(' · ').pop():['REISE','START','URLAUB','ANFANG'][id];
      this.text(x,220,value(previous),own==='a'?22:12,'#789da5');this.text(x,332,value(next),own==='a'?22:12,'#789da5');
      const t=this.ringTexts[i],changed=this.lastOrder&&this.lastOrder[i]!==item;t.setText(value(item)).setFontSize(own==='a'?44:17).setColor(matched?'#83e3c5':'#f5f4e9');
      if(changed&&!reduced){this.tweens.killTweensOf(t);t.y=290;t.alpha=.3;this.tweens.add({targets:t,y:275,alpha:1,duration:220,ease:'Cubic.easeOut'});}
      this.text(x,447,matched?'✓ EINGERASTET':`RING ${i+1}`,11,matched?'#83e3c5':'#c2d6d6');
     }
     this.lastOrder=[...p.order];
     this.message.setText(p.matched.every(Boolean)?'Alle vier Ringe passen. Bestätigt jetzt beide euren Schlüssel.':own==='a'?'Du drehst Zahlen. Dein Gegenüber kennt die Reihenfolge.':'Du drehst Kapitel. Dein Gegenüber kennt ihre Zahlen.');
    }else{
     const cell=36,ox=84,oy=72;
     this.badge.setText(`JAPAN CUP  ·  ${p.station.toUpperCase()}`);
     g.fillStyle(0x173941);g.fillRoundedRect(ox-8,oy-8,448,448,16);g.lineStyle(1,0x28505a);
     for(let i=0;i<=12;i++){g.lineBetween(ox+i*cell,oy,ox+i*cell,oy+432);g.lineBetween(ox,oy+i*cell,ox+432,oy+i*cell);}
     const tx=ox+p.target[0]*cell+18,ty=oy+p.target[1]*cell+18;
     g.fillStyle(p.target_owner===own?colors.gold:colors.mint);g.fillCircle(tx,ty,12);g.lineStyle(3,0xf5f4e9,.5);g.strokeCircle(tx,ty,16);
     p.body.forEach(([x,y],i)=>{g.fillStyle(i===0?colors.white:colors.mint);g.fillRoundedRect(ox+x*cell+3,oy+y*cell+3,30,30,9);if(i===0){g.fillStyle(colors.bg);g.fillCircle(ox+x*cell+11,oy+y*cell+12,3);g.fillCircle(ox+x*cell+24,oy+y*cell+12,3);}});
     const active=p.phase==='race'||p.practice;
     if(!active||p.paused){g.fillStyle(colors.bg,.9);g.fillRoundedRect(115,227,370,116,18);this.text(300,267,p.paused?'GEMEINSAM PAUSIERT':p.phase==='countdown'?`START IN ${p.countdown}`:p.phase==='passport'?'CUP IM ZIEL':p.ready[own]?'BEREIT. DU AUCH?':'DEIN JAPAN-CUP',22,'#ffcf73');this.text(300,304,p.phase==='warmup'?'Üben oder unten auf „Ich bin bereit“ tippen':'Zwei Schlangen. Ein gemeinsames Ziel.',13);}
     this.message.setText(p.phase==='race'?`Stempel für ${p.target_owner===own?'dich':s.partner}  ·  Pfeile / WASD / Wischen`:'Euer Reisepass entsteht zusammen.');
    }
   }
  }
  game=new Phaser.Game({type:Phaser.CANVAS,width:600,height:550,parent,backgroundColor:'#102b32',banner:false,audio:{noAudio:true},input:{keyboard:false},scale:{mode:Phaser.Scale.FIT,autoCenter:Phaser.Scale.CENTER_BOTH},scene:CupScene});
 }
 function update(s){pending=s;if(scene?.sys?.isActive())scene.paint(s);}
 function destroy(){if(game)game.destroy(true);game=null;scene=null;pending=null;}
 return{mount,update,destroy};
})();
