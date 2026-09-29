'use strict';
// CUPX1: 5-byte marker, 1-byte media type, then bytes XORed with the repeated UTF-8 key.
const cupKey=new TextEncoder().encode('CUP-LAB-2026');
const cupTypes={1:'image/svg+xml',2:'image/jpeg',3:'image/png',4:'image/webp'};
function decryptCup(buffer){
 const bytes=new Uint8Array(buffer);
 if(bytes.length<7||new TextDecoder().decode(bytes.subarray(0,5))!=='CUPX1'||!cupTypes[bytes[5]])throw new Error('Unbekanntes Fundstück.');
 const result=new Uint8Array(bytes.length-6);
 for(let i=0;i<result.length;i++)result[i]=bytes[i+6]^cupKey[i%cupKey.length];
 return new Blob([result],{type:cupTypes[bytes[5]]});
}
window.CupLab=Object.freeze({decrypt:decryptCup});
const cupUrls=[];
document.getElementById('lab-decrypt').addEventListener('click',async()=>{
 const button=document.getElementById('lab-decrypt'),status=document.getElementById('lab-status');
 button.disabled=true;status.textContent='Fundstücke werden entschlüsselt …';
 try{
  for(const image of document.querySelectorAll('[data-cup-image]')){
   const response=await fetch(`/lab/images/${image.dataset.cupImage}`);
   if(!response.ok)throw new Error('Ein Fundstück ist nicht erreichbar.');
   const url=URL.createObjectURL(decryptCup(await response.arrayBuffer()));
   cupUrls.push(url);image.src=url;
  }
  status.textContent='Drei Fundstücke entschlüsselt.';
 }catch(error){status.textContent=error.message;button.disabled=false;}
});
window.addEventListener('pagehide',()=>{for(const url of cupUrls)URL.revokeObjectURL(url);});
