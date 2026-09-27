'use strict';
const invitation=new URL(location.href);
const fragment=new URLSearchParams(invitation.hash.slice(1));
const password=fragment.get('password');
if(password!==null){
 history.replaceState(null,'',invitation.pathname+invitation.search);
 const form=document.querySelector('form[method="post"]');
 const input=document.getElementById('password');
 if(form&&input&&password.length<=256){input.value=password;form.requestSubmit();}
}
