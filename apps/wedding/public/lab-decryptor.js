'use strict';
// CUPX2: one authenticated gallery bundle, XORed with an AES-CTR keystream.
const encoder=new TextEncoder();
function fromHex(hex){
 if(!/^[0-9a-f]{64}$/i.test(hex))throw new Error('Galerieschlüssel fehlt.');
 return Uint8Array.from(hex.match(/../g),part=>parseInt(part,16));
}
async function derive(master,label){
 const root=await crypto.subtle.importKey('raw',master,{name:'HMAC',hash:'SHA-256'},false,['sign']);
 return new Uint8Array(await crypto.subtle.sign('HMAC',root,encoder.encode(label)));
}
async function decryptCup(bundle,keyHex){
 const bytes=new Uint8Array(bundle),marker=new TextDecoder().decode(bytes.subarray(0,5));
 if(bytes.length<54||marker!=='CUPX2')throw new Error('Unbekanntes Fundstück.');
 const master=fromHex(keyHex),nonce=bytes.subarray(5,21),tag=bytes.subarray(21,53),ciphertext=bytes.subarray(53);
 const macKey=await crypto.subtle.importKey('raw',await derive(master,'cup-gallery/mac'),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const signed=new Uint8Array(21+ciphertext.length);signed.set(bytes.subarray(0,21));signed.set(ciphertext,21);
 const actual=new Uint8Array(await crypto.subtle.sign('HMAC',macKey,signed));
 if(actual.some((value,index)=>value!==tag[index]))throw new Error('Prüfsumme stimmt nicht.');
 const aesKey=await crypto.subtle.importKey('raw',await derive(master,'cup-gallery/enc'),'AES-CTR',false,['decrypt']);
 const plain=await crypto.subtle.decrypt({name:'AES-CTR',counter:nonce,length:128},aesKey,ciphertext);
 const gallery=JSON.parse(new TextDecoder().decode(plain));
 if(gallery.version!==2||!Array.isArray(gallery.images))throw new Error('Unbekanntes Galerieformat.');
 return gallery.images;
}
window.CupLab=Object.freeze({decrypt:decryptCup});
const cupUrls=[];
document.getElementById('lab-decrypt').addEventListener('click',async()=>{
 const button=document.getElementById('lab-decrypt'),status=document.getElementById('lab-status'),grid=document.getElementById('lab-grid');
 button.disabled=true;status.textContent='Fundstücke werden entschlüsselt …';
 for(const url of cupUrls)URL.revokeObjectURL(url);cupUrls.length=0;grid.replaceChildren();
 try{
  const manifestResponse=await fetch('/lab/manifest.json');
  if(!manifestResponse.ok)throw new Error('Die Fundspur ist nicht erreichbar.');
  const manifest=await manifestResponse.json();
  const bundleResponse=await fetch(manifest.bundle);
  if(!bundleResponse.ok)throw new Error('Das verschlüsselte Archiv ist nicht erreichbar.');
  const images=await decryptCup(await bundleResponse.arrayBuffer(),manifest.key_hex);
  for(const item of images){
   if(!/^\d{2}$/.test(item.id)||!['image/jpeg','image/png','image/webp'].includes(item.mime))throw new Error('Ein Bild hat ein unbekanntes Format.');
   const raw=atob(item.data),bytes=Uint8Array.from(raw,char=>char.charCodeAt(0));
   const url=URL.createObjectURL(new Blob([bytes],{type:item.mime}));cupUrls.push(url);
   const figure=document.createElement('figure'),image=document.createElement('img'),caption=document.createElement('figcaption');
   image.src=url;image.alt=`Fundstück ${item.id}`;image.loading='lazy';caption.textContent=`Fundstück ${item.id}`;
   figure.append(image,caption);grid.append(figure);
  }
  status.textContent=`${images.length} Fundstücke entschlüsselt.`;
 }catch(error){status.textContent=error.message;button.disabled=false;}
});
window.addEventListener('pagehide',()=>{for(const url of cupUrls)URL.revokeObjectURL(url);});
