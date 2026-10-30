// SPDX-License-Identifier: MIT
// Keyboard/pointer flow adapted from the APDO KM003C controller.
"use strict";
const keyMap={KeyW:2,ArrowUp:2,KeyS:128,ArrowDown:128,KeyA:4,ArrowLeft:4,KeyD:8,ArrowRight:8,Space:1,ControlLeft:1,ControlRight:1,KeyE:16,Escape:32,Enter:64,NumpadEnter:64};
const $=id=>document.getElementById(id),pressed=new Map();
let token="",armed=false,stopped=false,sending=false,usbConnected=false,connectionId=null,pending=[],snapshot=0;
function mask(){let value=0;for(const bit of pressed.values())value|=bit;return value;}
function paint(){const value=mask();document.querySelectorAll("[data-mask]").forEach(b=>{const on=!!(value&Number(b.dataset.mask));b.classList.toggle("active",on);b.setAttribute("aria-pressed",String(on));});$("focus").textContent=armed?"Keyboard active":"Keyboard off";$("enable").textContent=armed?"Keyboard enabled":"Enable keyboard";}
async function post(path,data){const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-APDO-Token":token},body:JSON.stringify(data),keepalive:true});if(!response.ok)throw new Error("Waiting for the meter. Enable keyboard again after reconnecting.");return response;}
async function sendPending(){if(sending||!token||stopped)return;sending=true;try{while(pending.length&&!stopped){const item=pending.shift();await post(item.release?"/api/release":"/api/keys",item.release?{}:{buttons:item.buttons});}}catch(error){pending=[];pressed.clear();armed=false;paint();$("error").textContent=error.message;}finally{sending=false;}}
function queue(){const value=mask();if(pending.length>32){releaseAll();return;}if(pending.at(-1)?.buttons!==value)pending.push({buttons:value});paint();void sendPending();}
function releaseAll(){const owned=armed||pressed.size>0||pending.some(item=>item.buttons);pressed.clear();armed=false;pending=[];if(owned){pending.push({release:true});void sendPending();}paint();}
$("enable").addEventListener("click",()=>{if(usbConnected){armed=true;$("error").textContent="";paint();queue();}});
$("release").addEventListener("click",releaseAll);
window.addEventListener("keydown",event=>{if(!armed||!(event.code in keyMap))return;event.preventDefault();if(!pressed.has(event.code)){pressed.set(event.code,keyMap[event.code]);queue();}});
window.addEventListener("keyup",event=>{if(!(event.code in keyMap)||!pressed.has(event.code))return;event.preventDefault();pressed.delete(event.code);queue();});
window.addEventListener("blur",releaseAll);
document.addEventListener("visibilitychange",()=>{if(document.hidden)releaseAll();});
window.addEventListener("pagehide",releaseAll);
document.querySelectorAll("[data-mask]").forEach(button=>{
  button.addEventListener("pointerdown",event=>{if(!usbConnected||stopped)return;event.preventDefault();armed=true;button.setPointerCapture(event.pointerId);pressed.set(`pointer-${event.pointerId}`,Number(button.dataset.mask));queue();});
  const release=event=>{const id=`pointer-${event.pointerId}`;if(pressed.delete(id))queue();};
  button.addEventListener("pointerup",release);button.addEventListener("pointercancel",release);button.addEventListener("lostpointercapture",release);
});
$("preview-enabled").addEventListener("change",()=>void post("/api/preview",{enabled:$("preview-enabled").checked}).catch(error=>{$("error").textContent=error.message;}));
$("stop").addEventListener("click",async()=>{pressed.clear();armed=false;pending=[];stopped=true;paint();try{await post("/api/stop",{});}catch{}$("enable").disabled=true;$("connection").textContent="Server stopped";$("dot").classList.remove("connected");$("screen-info").textContent="Captured image · server stopped";});
async function status(){if(stopped)return;try{
  const state=await(await fetch("/api/status")).json();
  if(connectionId!==null&&state.connection_id!==connectionId)releaseAll();
  connectionId=state.connection_id;usbConnected=state.connected;
  $("enable").disabled=!usbConnected;$("dot").classList.toggle("connected",usbConnected);
  $("connection").textContent=usbConnected?"KWS-X1 connected":"Waiting for KWS-X1 v4…";
  $("performance").textContent=usbConnected?`Meter ${state.render_fps.toFixed(1)} fps · engine ${state.reply.frame_ms??"—"} ms`:"—";
  if(!usbConnected)releaseAll();
  $("error").textContent=state.error||"";
  if(state.screen){if(state.screen.snapshot!==snapshot){snapshot=state.screen.snapshot;$("screen").src=`/api/frame.bmp?snapshot=${snapshot}`;$("screen").hidden=false;$("screen-placeholder").hidden=true;$("save-frame").hidden=false;}
    $("screen-info").textContent=`120 × 90 · preview ${state.screen.preview_fps.toFixed(1)} fps · frame ${state.screen.game_frame}`;
  }else{$("screen").hidden=true;$("screen-placeholder").hidden=false;$("save-frame").hidden=true;$("screen-info").textContent="Waiting for capture…";snapshot=0;}
  $("preview-enabled").checked=state.preview_enabled;
  if(!state.preview_enabled)$("screen-info").textContent="Preview paused · playing on the meter";
}catch{usbConnected=false;$("enable").disabled=true;$("connection").textContent="Controller offline";$("dot").classList.remove("connected");releaseAll();}}
fetch("/api/session").then(r=>r.json()).then(s=>{token=s.token;void status();}).catch(error=>{$("error").textContent=error.message;});
setInterval(()=>{if(!stopped&&armed)queue();},100);
setInterval(status,300);paint();
