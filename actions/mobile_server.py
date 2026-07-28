from flask import request
# -*- coding: utf-8 -*-
"""
ERIS Mobile Companion – Servidor WebSocket + Web App para el celular.
Permite chatear con ERIS desde cualquier navegador en la misma red.
"""

import asyncio
import json
import socket
import threading
import websockets
from websockets import Request, Response
from websockets.datastructures import Headers

MOBILE_PORT = 8765
_connected_clients: set = set()
_loop: asyncio.AbstractEventLoop | None = None
_inject_callback = None

CHAT_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="theme-color" content="#0a0a1a">
<title>ERIS Mobile</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:#0a0a1a;font-family:-apple-system,system-ui,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e0e0e0}

/* Header */
.header{background:linear-gradient(135deg,#1a0533,#0d1b2a);padding:12px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(168,85,247,.3);position:relative;z-index:10}
.header .logo{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#a855f7,#7c3aed);display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:bold;color:#fff;flex-shrink:0}
.header .title{flex:1;font-size:16px;font-weight:600;letter-spacing:.5px}
.header .status{display:flex;align-items:center;gap:6px;font-size:11px;color:#888}
.header .status-dot{width:8px;height:8px;border-radius:50%;background:#555;transition:background .3s}
.header .status-dot.online{background:#34c759;box-shadow:0 0 8px rgba(52,199,89,.5)}
.header .status-dot.offline{background:#ff3b30;box-shadow:0 0 8px rgba(255,59,48,.3)}

/* Chat area */
.chat{flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:8px;scroll-behavior:smooth;background:radial-gradient(ellipse at 50% 0%,rgba(168,85,247,.03),transparent 70%)}
.chat::-webkit-scrollbar{width:3px}
.chat::-webkit-scrollbar-thumb{background:rgba(168,85,247,.3);border-radius:3px}

/* Bubbles */
.bubble{max-width:82%;padding:10px 14px;border-radius:16px;font-size:14px;line-height:1.5;word-wrap:break-word;animation:fadeIn .25s ease}
.bubble.user{align-self:flex-end;background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border-bottom-right-radius:4px}
.bubble.eris{align-self:flex-start;background:rgba(255,255,255,.06);border:1px solid rgba(168,85,247,.15);color:#e0e0e0;border-bottom-left-radius:4px}
.bubble.typing{align-self:flex-start;background:rgba(255,255,255,.04);border:1px solid rgba(168,85,247,.1);border-radius:16px;padding:12px 18px;display:flex;gap:4px;align-items:center}
.bubble.typing span{width:6px;height:6px;border-radius:50%;background:#888;animation:typing 1.2s infinite}
.bubble.typing span:nth-child(2){animation-delay:.2s}
.bubble.typing span:nth-child(3){animation-delay:.4s}
.bubble.system{align-self:center;background:transparent;color:#666;font-size:11px;text-align:center;padding:4px 8px}

@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes typing{0%,80%,100%{opacity:.3}40%{opacity:1}}

/* Input area */
.input-area{background:rgba(10,10,26,.95);border-top:1px solid rgba(168,85,247,.15);padding:10px 12px;display:flex;gap:8px;align-items:flex-end;backdrop-filter:blur(10px)}
.input-area textarea{flex:1;background:rgba(255,255,255,.05);border:1px solid rgba(168,85,247,.2);border-radius:20px;padding:10px 16px;color:#fff;font-size:14px;resize:none;outline:none;max-height:80px;font-family:inherit;line-height:1.4}
.input-area textarea:focus{border-color:#a855f7}
.input-area textarea::placeholder{color:#555}
.input-area .send-btn{width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#a855f7,#7c3aed);border:none;color:#fff;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:transform .15s,opacity .2s}
.input-area .send-btn:active{transform:scale(.9)}
.input-area .send-btn:disabled{opacity:.3;cursor:not-allowed}

/* Connection info banner */
.info-banner{background:rgba(255,59,48,.1);border:1px solid rgba(255,59,48,.3);color:#ff3b30;text-align:center;padding:8px;font-size:12px;display:none}

/* Utility */
.flex-col{display:flex;flex-direction:column;height:100%}
.hidden{display:none}
</style>
</head>
<body>
<div class="flex-col">
<div class="header">
<div class="logo">E</div>
<div class="title">ERIS Companion</div>
<div class="status"><span class="status-dot offline" id="statusDot"></span><span id="statusText">Desconectado</span></div>
</div>
<div class="info-banner" id="infoBanner"></div>
<div class="chat" id="chat"></div>
<div class="input-area">
<textarea id="input" placeholder="Escribe un mensaje..." rows="1" enterkeyhint="send"></textarea>
<button class="send-btn" id="sendBtn" disabled>&#10148;</button>
</div>
</div>

<script>
(function(){
const chat=document.getElementById('chat');
const input=document.getElementById('input');
const sendBtn=document.getElementById('sendBtn');
const statusDot=document.getElementById('statusDot');
const statusText=document.getElementById('statusText');
const infoBanner=document.getElementById('infoBanner');

let ws=null;
let reconnectTimer=null;

function getWsUrl(){
const loc=window.location;
const proto=loc.protocol==='https:'?'wss:':'ws:';
return proto+'//'+loc.host;
}

function addBubble(text,type){
const b=document.createElement('div');
b.className='bubble '+type;
b.textContent=text;
chat.appendChild(b);
chat.scrollTop=chat.scrollHeight;
}

function showTyping(){
const t=document.createElement('div');
t.className='bubble typing';
t.id='typingIndicator';
t.innerHTML='<span></span><span></span><span></span>';
chat.appendChild(t);
chat.scrollTop=chat.scrollHeight;
}

function hideTyping(){
const t=document.getElementById('typingIndicator');
if(t)t.remove();
}

function setStatus(online){
statusDot.className='status-dot '+(online?'online':'offline');
statusText.textContent=online?'Conectado':'Desconectado';
sendBtn.disabled=!online;
}

function showInfo(msg,isError=true){
infoBanner.textContent=msg;
infoBanner.style.display='block';
if(isError)setTimeout(()=>{infoBanner.style.display='none'},5000);
else infoBanner.style.display='none';
}

function connect(){
if(ws){ws.close();ws=null}
setStatus(false);
try{
ws=new WebSocket(getWsUrl());
}catch(e){
showInfo('Error al conectar: '+e.message);
scheduleReconnect();
return;
}

ws.onopen=function(){
setStatus(true);
showInfo('Conectado a ERIS',false);
addBubble('Conectado a ERIS','system');
clearTimeout(reconnectTimer);
};

ws.onclose=function(){
setStatus(false);
addBubble('Desconectado','system');
scheduleReconnect();
};

ws.onerror=function(){
setStatus(false);
showInfo('Error de conexión. Reintentando...');
};

ws.onmessage=function(event){
try{
const data=JSON.parse(event.data);
if(data.type==='message'){
hideTyping();
addBubble(data.text,'eris');
}else if(data.type==='ack'){
hideTyping();
}
}catch(e){
console.warn('WS parse error:',e);
}
};
}

function scheduleReconnect(){
clearTimeout(reconnectTimer);
reconnectTimer=setTimeout(connect,3000);
}

function sendMessage(){
const text=input.value.trim();
if(!text||!ws||ws.readyState!==WebSocket.OPEN)return;
input.value='';
addBubble(text,'user');
showTyping();
ws.send(JSON.stringify({type:'message',text}));
autoResize();
}

// Auto-resize textarea
function autoResize(){
input.style.height='auto';
input.style.height=Math.min(input.scrollHeight,80)+'px';
}
input.addEventListener('input',autoResize);

// Send on Enter (Shift+Enter for newline)
input.addEventListener('keydown',function(e){
if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}
});

sendBtn.addEventListener('click',sendMessage);

// Initial connect
connect();
})();
</script>
</body>
</html>'''


def _get_local_ip() -> str:
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start(port: int = 8765, inject_callback=None) -> str:
    """Start the mobile server in a daemon thread. Returns the HTTP URL."""
    global _inject_callback
    _inject_callback = inject_callback

    def _run():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(_serve(port))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    ip = _get_local_ip()
    return f"http://{ip}:{port}"


async def _serve(port: int):
    async def handler(websocket):
        _connected_clients.add(websocket)
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "message":
                    text = data.get("text", "").strip()
                    if text and _inject_callback:
                        _inject_callback(text)
                    await websocket.send(json.dumps({"type": "ack", "text": text}))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            _connected_clients.discard(websocket)

    async def process_request(connection, request: Request):
        upgrade = request.headers.get("Upgrade", "").lower()
        if upgrade == "websocket":
            return None
        if request.path == "/":
            return Response(200, "OK", Headers({"Content-Type": "text/html; charset=utf-8"}), CHAT_HTML.encode())
        if request.path == "/health":
            return Response(200, "OK", Headers({"Content-Type": "application/json"}), b'{"status":"ok"}')
        return None

    async with websockets.serve(
        handler,
        host="0.0.0.0",
        port=port,
        process_request=process_request,
    ):
        print(f"[MOBILE] Compañero iniciado en puerto {port}")
        await asyncio.Future()


def broadcast(text: str):
    """Thread-safe broadcast to all connected mobile clients."""
    if not _loop:
        return
    asyncio.run_coroutine_threadsafe(_broadcast(text), _loop)


async def _broadcast(text: str):
    if not _connected_clients:
        return
    message = json.dumps({"type": "message", "text": text})
    await asyncio.gather(
        *(c.send(message) for c in _connected_clients.copy()),
        return_exceptions=True,
    )
