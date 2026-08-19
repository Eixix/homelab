import * as THREE from './three.module.js';

const ease = x => 1 - (1 - x) ** 3;
const tween = (ms, draw) => new Promise(resolve => { const start = performance.now(); const frame = now => { const p = Math.min(1, (now - start) / ms); draw(ease(p)); p < 1 ? requestAnimationFrame(frame) : resolve(); }; requestAnimationFrame(frame); });

function texture(items, lid = false) {
  const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 700; const c = canvas.getContext('2d');
  c.fillStyle = lid ? '#eeeae1' : '#fffdf1'; c.fillRect(0, 0, 1024, 700);
  if (lid) { c.globalAlpha=.16; for(let i=0;i<4200;i++){const shade=150+Math.random()*95;c.fillStyle=`rgb(${shade},${shade},${shade-4})`;c.fillRect(Math.random()*1024,Math.random()*700,Math.random()*4+1,1)} c.globalAlpha=1; }
  c.strokeStyle = '#171717'; c.lineWidth = 16; c.strokeRect(35, 35, 954, 630); c.fillStyle = '#171717';
  if (lid) { c.textAlign = 'center'; c.font = 'bold 120px sans-serif'; c.fillText('PIZZA', 512, 290); c.fillText('UM ZWÖLF.', 512, 435); c.font = 'bold 27px monospace'; c.fillText('VORSICHT // GUTE ENTSCHEIDUNG', 512, 565); }
  else { c.font = 'bold 62px sans-serif'; c.fillText('PIZZA-MENÜ', 65, 105); c.font = '32px monospace'; items.slice(0, 6).forEach((item, i) => { const y = 185 + i * 68; c.fillText(item.name.slice(0, 27), 65, y); c.textAlign = 'right'; c.fillText(`${(item.priceCents / 100).toFixed(2)} €`, 950, y); c.textAlign = 'left'; c.beginPath(); c.moveTo(65, y + 16); c.lineTo(950, y + 16); c.lineWidth = 2; c.stroke(); }); c.fillStyle = '#f04432'; c.font = 'bold 28px monospace'; c.fillText('HIER REINFALLEN ZUM BESTELLEN →', 65, 645); }
  const result = new THREE.CanvasTexture(canvas); result.colorSpace = THREE.SRGBColorSpace; return result;
}

function cardboardTexture(color) {
  const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;const c=canvas.getContext('2d');c.fillStyle=color;c.fillRect(0,0,256,256);c.globalAlpha=.16;
  for(let i=0;i<2300;i++){const shade=145+Math.random()*100;c.fillStyle=`rgb(${shade},${shade},${shade-3})`;c.fillRect(Math.random()*256,Math.random()*256,Math.random()*3+1,1)}
  c.globalAlpha=.08;for(let y=8;y<256;y+=13){c.fillStyle='#77736d';c.fillRect(0,y,256,1)}c.globalAlpha=1;const result=new THREE.CanvasTexture(canvas);result.colorSpace=THREE.SRGBColorSpace;result.wrapS=result.wrapT=THREE.RepeatWrapping;return result;
}

function countdownTexture() {
  const canvas=document.createElement('canvas');canvas.width=768;canvas.height=220;const c=canvas.getContext('2d');const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
  const draw=text=>{c.clearRect(0,0,768,220);c.fillStyle='#f04432';c.fillRect(0,0,768,220);c.strokeStyle='#171717';c.lineWidth=18;c.strokeRect(9,9,750,202);c.fillStyle='#fff';c.textAlign='center';c.textBaseline='middle';c.font='bold 44px monospace';c.fillText(text,384,110,690);map.needsUpdate=true};draw('10:30');return{map,draw};
}

export function createPizzaBoxScene(canvas, items) {
  const stage = canvas.closest('.box-stage'); let isPacked = false;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }); renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.shadowMap.enabled = true;
  const scene = new THREE.Scene(); const camera = new THREE.PerspectiveCamera(38, 1, .1, 100); camera.up.set(0,0,-1); const centerTarget = new THREE.Vector3(0, .3, 0); const menuTarget = new THREE.Vector3(1.65, .25, 0); const target = centerTarget.clone(); scene.add(new THREE.HemisphereLight(0xfff2d6, 0x4b2d1c, 2.5)); const light = new THREE.DirectionalLight(0xffffff, 3.5); light.position.set(-7, 11, 9); light.castShadow = true; scene.add(light);
  const group = new THREE.Group(); scene.add(group); const card = new THREE.MeshStandardMaterial({ map:cardboardTexture('#eeeae1'), roughness: .94 }); const dark = new THREE.MeshStandardMaterial({ map:cardboardTexture('#d3cec4'), roughness: .97 });
  const add = (size, pos, material = card, parent = group) => { const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material); mesh.position.set(...pos); mesh.castShadow = mesh.receiveShadow = true; parent.add(mesh); return mesh; };
  add([7,.28,7],[0,0,0]); add([7.25,.85,.25],[0,.48,3.42],dark); add([7.25,.85,.25],[0,.48,-3.42],dark); add([.25,.85,6.6],[-3.38,.48,0],dark); add([.25,.85,6.6],[3.38,.48,0],dark);
  const pizzaPart=(geometry,color,y,x=-1.15,z=0)=>{const value=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color,roughness:.82}));value.position.set(x,y,z);value.castShadow=true;group.add(value)};
  pizzaPart(new THREE.CylinderGeometry(2.38,2.38,.16,64),0xb96d2f,.22); pizzaPart(new THREE.CylinderGeometry(2.18,2.18,.08,64),0xf2c64d,.34);
  [[-2.1,-.8],[-.55,-1.15],[-1.25,.65],[-.2,.55],[-1.9,1.25],[-.7,1.45]].forEach(([x,z])=>pizzaPart(new THREE.CylinderGeometry(.3,.3,.06,24),0xc94b32,.41,x,z));
  const menu = new THREE.Mesh(new THREE.PlaneGeometry(3.45,4.5),new THREE.MeshStandardMaterial({map:texture(items),roughness:.8})); menu.rotation.x=-Math.PI/2; menu.rotation.z=-.06; menu.position.set(1.75,.48,0); menu.castShadow=true; group.add(menu);
  const hinge = new THREE.Group(); hinge.position.set(0,.93,-3.52); group.add(hinge); const lidMats=[dark,dark,new THREE.MeshStandardMaterial({map:texture(items,true),roughness:.94}),dark,dark,dark]; add([7.15,.3,7.15],[0,0,3.575],lidMats,hinge);
  const countdown=countdownTexture();const notice=new THREE.Mesh(new THREE.PlaneGeometry(2.85,.82),new THREE.MeshBasicMaterial({map:countdown.map,transparent:true}));notice.rotation.x=-Math.PI/2;notice.position.set(2.15,.17,1.35);hinge.add(notice);
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(30,24),new THREE.ShadowMaterial({opacity:.2})); ground.rotation.x=-Math.PI/2; ground.position.y=-.18; ground.receiveShadow=true; scene.add(ground);
  const start=new THREE.Vector3(0,14.5,3.2), packed=new THREE.Vector3(0,15.5,0), dive=new THREE.Vector3(1.65,1.25,.55);
  const placeReceipt=()=>{if(!isPacked)return;const cr=canvas.getBoundingClientRect(),sr=stage.getBoundingClientRect();const project=(x,z)=>{const p=new THREE.Vector3(x,1.1,z).project(camera);return{x:cr.left-sr.left+(p.x+1)*cr.width/2,y:cr.top-sr.top+(1-p.y)*cr.height/2}};const left=project(-3.5,0),right=project(3.5,0),center=project(0,0);stage.style.setProperty('--receipt-left',`${center.x}px`);stage.style.setProperty('--receipt-top',`${center.y}px`);stage.style.setProperty('--receipt-width',`${Math.max(150,Math.abs(right.x-left.x)*.38)}px`)};
  const render=()=>{camera.lookAt(target);renderer.render(scene,camera);placeReceipt()};
  new ResizeObserver(()=>{const r=canvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/Math.max(1,r.height);camera.updateProjectionMatrix();render()}).observe(canvas);
  const openState=()=>{isPacked=false;camera.position.copy(start);target.copy(centerTarget);camera.fov=38;camera.updateProjectionMatrix();hinge.rotation.x=-1.82;canvas.style.opacity='1';render()}; openState();
  return { setCountdown(text){countdown.draw(text);render()}, async intro(){isPacked=false;camera.position.copy(start);target.copy(centerTarget);hinge.rotation.x=0;canvas.style.opacity='1';await tween(950,p=>{hinge.rotation.x=-1.82*p;render()});await tween(1250,p=>{camera.position.lerpVectors(start,dive,p);target.lerpVectors(centerTarget,menuTarget,p);camera.fov=38+25*p;camera.updateProjectionMatrix();canvas.style.opacity=String(1-Math.max(0,(p-.76)/.24));render()})}, async close(){openState();await tween(900,p=>{hinge.rotation.x=-1.82*(1-p);camera.position.lerpVectors(start,packed,p);render()});isPacked=true;render()}, packed(){isPacked=true;hinge.rotation.x=0;camera.position.copy(packed);target.copy(centerTarget);canvas.style.opacity='1';render()}, async open(){isPacked=false;target.copy(centerTarget);await tween(850,p=>{hinge.rotation.x=-1.82*p;camera.position.lerpVectors(packed,start,p);render()})} };
}
