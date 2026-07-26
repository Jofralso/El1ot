"""
ELIOT Touch UI

Animated cyberpunk web interface with CSS avatar, WebSocket real-time state,
chat, dashboard, knowledge search, and workflow execution.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["ui"])

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>ELIOT - Cybersecurity Operations Terminal</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700&display=swap');

:root {
  --green: #00ff41;
  --green-dim: #00cc33;
  --green-glow: rgba(0,255,65,0.3);
  --orange: #ff6600;
  --red: #ff0040;
  --cyan: #00e5ff;
  --bg: #050508;
  --panel: #0a0a0f;
  --border: #1a1a2e;
  --text: #c0c0c0;
}

* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; overflow:hidden; }

body {
  font-family: 'Share Tech Mono', 'Courier New', monospace;
  background: var(--bg);
  color: var(--text);
}

/* ── Scanline overlay ── */
body::after {
  content:'';
  position:fixed; inset:0; z-index:9999;
  background: repeating-linear-gradient(
    0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px
  );
  pointer-events:none;
}

/* ── Header ── */
.header {
  height:48px;
  background: linear-gradient(180deg, #0d0d14 0%, #080810 100%);
  border-bottom:1px solid var(--border);
  display:flex; align-items:center; justify-content:space-between;
  padding:0 20px;
  position:relative;
}
.header::after {
  content:''; position:absolute; bottom:0; left:0; right:0; height:1px;
  background: linear-gradient(90deg, transparent, var(--green), transparent);
  opacity:0.5;
}
.logo {
  font-family:'Orbitron', monospace;
  font-size:20px; font-weight:700;
  color:var(--green);
  text-shadow: 0 0 10px var(--green-glow), 0 0 20px var(--green-glow);
  letter-spacing:3px;
}
.header-status {
  display:flex; align-items:center; gap:16px; font-size:12px;
}
.status-dot {
  width:8px; height:8px; border-radius:50%;
  background:var(--green);
  box-shadow: 0 0 6px var(--green);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%,100% { opacity:1; } 50% { opacity:0.4; }
}
.status-label { color:#666; }
.status-value { color:var(--green); }

/* ── Navigation ── */
.nav {
  height:40px;
  display:flex; gap:2px;
  padding:0 12px;
  background: var(--panel);
  border-bottom:1px solid var(--border);
  align-items:center;
}
.nav-btn {
  background:transparent; border:1px solid transparent;
  color:#555; padding:6px 16px;
  font-family:inherit; font-size:12px;
  cursor:pointer; text-transform:uppercase;
  letter-spacing:1px; transition:all 0.2s;
  position:relative;
}
.nav-btn:hover { color:var(--green); border-color:#1a1a2e; }
.nav-btn.active {
  color:var(--green); border-color:var(--green);
  background:rgba(0,255,65,0.05);
  text-shadow:0 0 8px var(--green-glow);
}
.nav-btn.active::after {
  content:''; position:absolute; bottom:-1px; left:20%; right:20%; height:1px;
  background:var(--green);
}

/* ── Pages ── */
.page {
  display:none;
  height:calc(100vh - 88px);
  overflow-y:auto;
  padding:16px;
  animation: fadeIn 0.3s ease;
}
.page.active { display:block; }
@keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:#1a1a2e; border-radius:2px; }
::-webkit-scrollbar-thumb:hover { background:var(--green-dim); }

/* ── Cards ── */
.card {
  background: var(--panel);
  border:1px solid var(--border);
  padding:16px; margin-bottom:12px;
  position:relative;
  overflow:hidden;
}
.card::before {
  content:''; position:absolute; top:0; left:0; width:3px; height:100%;
  background:var(--green); opacity:0.6;
}
.card h3 {
  font-family:'Orbitron', monospace;
  font-size:11px; color:var(--green);
  text-transform:uppercase; letter-spacing:2px;
  margin-bottom:12px;
  display:flex; align-items:center; gap:8px;
}
.card h3::before { content:'>'; color:var(--green); }

.metric-row {
  display:flex; justify-content:space-between; align-items:center;
  padding:6px 0; border-bottom:1px solid #0d0d14;
  font-size:13px;
}
.metric-row:last-child { border-bottom:none; }
.metric-label { color:#555; }
.metric-value { color:var(--green); font-weight:bold; }
.metric-bar {
  height:4px; background:#111; border-radius:2px; margin-top:4px; overflow:hidden;
}
.metric-bar-fill {
  height:100%; border-radius:2px;
  background: linear-gradient(90deg, var(--green-dim), var(--green));
  transition: width 0.5s ease;
  box-shadow: 0 0 6px var(--green-glow);
}

/* ── Avatar ── */
.avatar-container {
  display:flex; flex-direction:column; align-items:center;
  padding:20px 0;
  position:relative;
}
.avatar-face {
  width:220px; height:220px;
  position:relative;
  border-radius:50%;
  background: radial-gradient(circle at 50% 40%, #0f0f1a 0%, #08080f 50%, #030306 100%);
  border:2px solid var(--border);
  box-shadow: 
    0 0 30px rgba(0,255,65,0.1), 
    inset 0 0 40px rgba(0,255,65,0.03),
    inset 0 -20px 40px rgba(0,0,0,0.5);
  transition: border-color 0.5s, box-shadow 0.5s;
  overflow:hidden;
}
.avatar-face::before {
  content:''; position:absolute; inset:0; border-radius:50%;
  background: radial-gradient(ellipse at 30% 20%, rgba(255,255,255,0.03) 0%, transparent 50%);
  pointer-events:none;
}
.avatar-face.state-thinking {
  border-color: var(--cyan);
  box-shadow: 
    0 0 50px rgba(0,229,255,0.25), 
    inset 0 0 40px rgba(0,229,255,0.05),
    inset 0 -20px 40px rgba(0,0,0,0.5);
}
.avatar-face.state-alert {
  border-color: var(--red);
  box-shadow: 
    0 0 60px rgba(255,0,64,0.35), 
    inset 0 0 40px rgba(255,0,64,0.08),
    inset 0 -20px 40px rgba(0,0,0,0.5);
  animation: alert-pulse 0.8s infinite;
}
@keyframes alert-pulse {
  0%,100% { box-shadow: 0 0 60px rgba(255,0,64,0.35), inset 0 0 40px rgba(255,0,64,0.08); }
  50% { box-shadow: 0 0 80px rgba(255,0,64,0.5), inset 0 0 50px rgba(255,0,64,0.12); }
}
.avatar-face.state-speaking {
  border-color: var(--green);
  box-shadow: 
    0 0 60px var(--green-glow), 
    inset 0 0 40px rgba(0,255,65,0.06),
    inset 0 -20px 40px rgba(0,0,0,0.5);
}

/* ── Face structure ── */
.avatar-brow {
  position:absolute; top:28%; left:50%; transform:translateX(-50%);
  display:flex; gap:50px;
  z-index:2;
}
.avatar-brow-line {
  width:24px; height:2px;
  background: var(--green);
  border-radius:1px;
  opacity:0.4;
  transition: transform 0.3s, opacity 0.3s;
}
.avatar-face.state-thinking .avatar-brow-line { transform:translateY(-2px); opacity:0.6; }
.avatar-face.state-alert .avatar-brow-line { transform:translateY(2px) rotate(-5deg); opacity:0.8; }

/* ── Eyes ── */
.avatar-eyes {
  position:absolute; top:38%; left:50%; transform:translate(-50%,-50%);
  display:flex; gap:36px;
  z-index:3;
}
.eye {
  width:32px; height:32px;
  border-radius:50%;
  background: radial-gradient(circle, #000 0%, #000 40%, rgba(0,255,65,0.1) 70%, transparent 100%);
  border: 1.5px solid rgba(0,255,65,0.4);
  position:relative;
  overflow:hidden;
}
.eye::before {
  content:''; position:absolute; inset:0; border-radius:50%;
  background: radial-gradient(circle, transparent 30%, rgba(0,255,65,0.05) 100%);
  animation: eye-glow 3s ease-in-out infinite;
}
@keyframes eye-glow {
  0%,100% { opacity:0.5; } 50% { opacity:1; }
}
.eye .iris {
  width:18px; height:18px;
  border-radius:50%;
  background: radial-gradient(circle, var(--green) 0%, var(--green-dim) 50%, rgba(0,200,50,0.6) 100%);
  position:absolute; top:50%; left:50%;
  transform:translate(-50%,-50%);
  box-shadow: 0 0 15px var(--green-glow), 0 0 30px rgba(0,255,65,0.2);
  transition: transform 0.3s ease;
  animation: iris-pulse 4s ease-in-out infinite;
}
@keyframes iris-pulse {
  0%,100% { box-shadow: 0 0 15px var(--green-glow), 0 0 30px rgba(0,255,65,0.2); }
  50% { box-shadow: 0 0 20px var(--green-glow), 0 0 40px rgba(0,255,65,0.3); }
}
.eye .pupil {
  width:8px; height:8px;
  border-radius:50%;
  background:#000;
  position:absolute; top:50%; left:50%;
  transform:translate(-50%,-50%);
  transition: transform 0.3s ease;
}
.eye .pupil::after {
  content:''; position:absolute; top:1px; left:1px;
  width:3px; height:3px; border-radius:50%;
  background:rgba(255,255,255,0.7);
}
@keyframes blink {
  0%,42%,46%,100% { transform:scaleY(1); }
  44% { transform:scaleY(0.05); }
}
.eye.look-left .iris { transform:translate(-70%,-50%); }
.eye.look-left .pupil { transform:translate(-80%,-50%); }
.eye.look-right .iris { transform:translate(0%,-50%); }
.eye.look-right .pupil { transform:translate(0%,-50%); }
.eye.look-up .iris { transform:translate(-50%,-70%); }
.eye.look-up .pupil { transform:translate(-50%,-80%); }
.eye.look-down .iris { transform:translate(-50%,0%); }
.eye.look-down .pupil { transform:translate(-50%,0%); }

/* ── Nose ── */
.avatar-nose {
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  width:2px; height:12px;
  background: linear-gradient(180deg, transparent, rgba(0,255,65,0.15), transparent);
  border-radius:1px;
}

/* ── Mouth ── */
.avatar-mouth {
  position:absolute; bottom:26%; left:50%; transform:translateX(-50%);
  width:44px; height:3px;
  background: linear-gradient(90deg, transparent 0%, var(--green) 20%, var(--green) 80%, transparent 100%);
  border-radius:2px;
  box-shadow: 0 0 10px var(--green-glow);
  transition: all 0.15s ease;
  z-index:3;
}
.avatar-mouth.speaking {
  height:18px; border-radius:10px;
  animation: talk 0.12s infinite alternate;
  background: var(--green);
}
@keyframes talk {
  0% { height:4px; border-radius:2px; }
  25% { height:12px; border-radius:6px; }
  50% { height:18px; border-radius:10px; }
  75% { height:8px; border-radius:4px; }
  100% { height:14px; border-radius:8px; }
}
.avatar-mouth.smile {
  width:36px; height:16px;
  border-radius: 0 0 18px 18px;
  border-top:none;
  background: var(--green);
}
.avatar-mouth.frown {
  width:36px; height:12px;
  border-radius: 18px 18px 0 0;
  border-bottom:none;
  background: var(--green);
}

/* ── Avatar rings ── */
.avatar-ring {
  position:absolute; inset:-12px;
  border-radius:50%;
  border:1px solid rgba(0,255,65,0.12);
  animation: ring-rotate 25s linear infinite;
}
.avatar-ring::before {
  content:''; position:absolute; top:-2px; left:50%; width:4px; height:4px;
  background:var(--green); border-radius:50%;
  box-shadow: 0 0 10px var(--green);
}
.avatar-ring-outer {
  position:absolute; inset:-20px;
  border-radius:50%;
  border:1px dashed rgba(0,255,65,0.06);
  animation: ring-rotate 40s linear infinite reverse;
}
.avatar-ring-outer::before {
  content:''; position:absolute; bottom:-2px; right:20%; width:3px; height:3px;
  background:var(--cyan); border-radius:50%;
  box-shadow: 0 0 8px var(--cyan);
}
@keyframes ring-rotate { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }

/* ── Scan line ── */
.avatar-scanline {
  position:absolute; left:10%; right:10%; height:1px;
  background: linear-gradient(90deg, transparent, rgba(0,255,65,0.3), transparent);
  animation: scanline 4s ease-in-out infinite;
  pointer-events:none;
  z-index:4;
}
@keyframes scanline {
  0% { top:20%; opacity:0; }
  10% { opacity:1; }
  90% { opacity:1; }
  100% { top:80%; opacity:0; }
}

/* ── Data particles ── */
.avatar-particles {
  position:absolute; inset:0; border-radius:50%; overflow:hidden;
  pointer-events:none;
  z-index:1;
}
.avatar-particle {
  position:absolute;
  width:2px; height:2px;
  background:var(--green);
  border-radius:50%;
  opacity:0;
  animation: particle-float 3s ease-in-out infinite;
}
.avatar-particle:nth-child(1) { left:20%; animation-delay:0s; }
.avatar-particle:nth-child(2) { left:40%; animation-delay:0.5s; }
.avatar-particle:nth-child(3) { left:60%; animation-delay:1s; }
.avatar-particle:nth-child(4) { left:80%; animation-delay:1.5s; }
.avatar-particle:nth-child(5) { left:30%; animation-delay:2s; }
.avatar-particle:nth-child(6) { left:70%; animation-delay:2.5s; }
@keyframes particle-float {
  0% { bottom:10%; opacity:0; }
  20% { opacity:0.8; }
  80% { opacity:0.8; }
  100% { bottom:90%; opacity:0; }
}

.avatar-state-label {
  margin-top:20px;
  font-family:'Orbitron', monospace;
  font-size:13px;
  color:var(--green);
  text-transform:uppercase;
  letter-spacing:4px;
  text-shadow:0 0 12px var(--green-glow);
}
.avatar-emotion-label {
  margin-top:4px;
  font-size:11px; color:#555;
}

/* ── Chat ── */
.chat-container {
  display:flex; flex-direction:column;
  height:calc(100vh - 104px);
}
.chat-messages {
  flex:1; overflow-y:auto;
  padding:12px;
  display:flex; flex-direction:column; gap:8px;
}
.chat-msg {
  max-width:80%; padding:10px 14px;
  font-size:13px; line-height:1.5;
  border-radius:2px;
  animation: msg-in 0.2s ease;
  word-wrap:break-word;
  white-space:pre-wrap;
}
@keyframes msg-in { from { opacity:0; transform:translateY(8px); } }
.chat-msg.user {
  align-self:flex-end;
  background:rgba(255,102,0,0.1);
  border:1px solid rgba(255,102,0,0.3);
  color:var(--orange);
}
.chat-msg.agent {
  align-self:flex-start;
  background:rgba(0,255,65,0.05);
  border:1px solid rgba(0,255,65,0.2);
  color:var(--text);
}
.chat-msg .msg-sender {
  font-family:'Orbitron', monospace;
  font-size:9px; text-transform:uppercase;
  letter-spacing:1px; margin-bottom:4px;
  opacity:0.6;
}
.chat-msg.user .msg-sender { color:var(--orange); }
.chat-msg.agent .msg-sender { color:var(--green); }

.typing-indicator {
  display:flex; gap:4px; padding:10px 14px; align-self:flex-start;
  background:rgba(0,255,65,0.05); border:1px solid rgba(0,255,65,0.2);
  border-radius:2px;
}
.typing-dot {
  width:6px; height:6px; border-radius:50%;
  background:var(--green); opacity:0.4;
  animation: typing-bounce 1.2s infinite;
}
.typing-dot:nth-child(2) { animation-delay:0.2s; }
.typing-dot:nth-child(3) { animation-delay:0.4s; }
@keyframes typing-bounce {
  0%,60%,100% { opacity:0.4; transform:translateY(0); }
  30% { opacity:1; transform:translateY(-4px); }
}

.chat-input-bar {
  display:flex; gap:8px; padding:12px;
  background:var(--panel);
  border-top:1px solid var(--border);
}
.chat-input-bar input {
  flex:1; background:#0a0a0f;
  border:1px solid var(--border); color:var(--green);
  padding:10px 14px; font-family:inherit; font-size:13px;
  outline:none; transition:border-color 0.2s;
}
.chat-input-bar input:focus { border-color:var(--green); }
.chat-input-bar input::placeholder { color:#333; }
.chat-input-bar button {
  background:var(--green); color:#000; border:none;
  padding:10px 20px; font-family:inherit; font-size:12px;
  font-weight:bold; cursor:pointer; text-transform:uppercase;
  letter-spacing:1px; transition:all 0.2s;
}
.chat-input-bar button:hover {
  background:#33ff66;
  box-shadow:0 0 12px var(--green-glow);
}

/* ── Knowledge ── */
.kb-search {
  display:flex; gap:8px; margin-bottom:12px;
}
.kb-search input {
  flex:1; background:#0a0a0f;
  border:1px solid var(--border); color:var(--green);
  padding:10px 14px; font-family:inherit; font-size:13px;
  outline:none;
}
.kb-search input:focus { border-color:var(--green); }
.kb-search button {
  background:var(--green); color:#000; border:none;
  padding:10px 16px; font-family:inherit; cursor:pointer;
  font-weight:bold; text-transform:uppercase; font-size:12px;
}
.kb-result {
  padding:10px; background:#08080c; border:1px solid var(--border);
  margin-bottom:8px; font-size:12px; line-height:1.5;
}
.kb-result .kb-source { color:var(--cyan); font-size:10px; text-transform:uppercase; }
.kb-result .kb-score { color:#555; font-size:10px; float:right; }
.kb-result .kb-text { color:#888; margin-top:4px; }

/* ── Workflows ── */
.workflow-card {
  background:var(--panel); border:1px solid var(--border);
  padding:14px; margin-bottom:8px; cursor:pointer;
  transition:all 0.2s; position:relative;
}
.workflow-card:hover {
  border-color:var(--green);
  background:rgba(0,255,65,0.03);
}
.workflow-card h4 {
  color:var(--green); font-size:13px; margin-bottom:4px;
  font-family:'Orbitron', monospace; text-transform:uppercase;
  letter-spacing:1px;
}
.workflow-card p { color:#555; font-size:11px; }
.workflow-card .wf-agents {
  display:flex; gap:4px; margin-top:8px; flex-wrap:wrap;
}
.wf-agent-tag {
  background:rgba(0,255,65,0.1); border:1px solid rgba(0,255,65,0.2);
  color:var(--green); padding:2px 8px; font-size:9px;
  text-transform:uppercase; letter-spacing:1px;
}

/* ── Boot animation ── */
.boot-screen {
  position:fixed; inset:0; z-index:10000;
  background:var(--bg);
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  transition: opacity 0.8s ease;
}
.boot-screen.hidden { opacity:0; pointer-events:none; }
.boot-text {
  font-family:'Share Tech Mono', monospace;
  color:var(--green); font-size:14px;
  text-align:left; line-height:1.8;
  max-width:500px;
}
.boot-cursor {
  display:inline-block; width:8px; height:14px;
  background:var(--green); animation: cursor-blink 0.6s infinite;
  vertical-align:middle; margin-left:2px;
}
@keyframes cursor-blink { 0%,100% { opacity:1; } 50% { opacity:0; } }
.boot-progress {
  width:300px; height:2px; background:#111; margin-top:24px;
  border-radius:1px; overflow:hidden;
}
.boot-progress-fill {
  height:100%; width:0%; background:var(--green);
  transition: width 0.3s ease;
  box-shadow:0 0 8px var(--green-glow);
}
</style>
</head>
<body>

<!-- Boot Screen -->
<div class="boot-screen" id="boot-screen">
  <div class="boot-text" id="boot-text"></div>
  <div class="boot-progress"><div class="boot-progress-fill" id="boot-progress"></div></div>
</div>

<!-- Main App (hidden during boot) -->
<div id="app" style="display:none">
  <div class="header">
    <div class="logo">ELIOT</div>
    <div class="header-status">
      <div class="status-dot" id="status-dot"></div>
      <span class="status-label">SYS</span>
      <span class="status-value" id="status-text">INIT</span>
    </div>
  </div>
  <div class="nav">
    <button class="nav-btn active" data-page="home">Interface</button>
    <button class="nav-btn" data-page="chat">Chat</button>
    <button class="nav-btn" data-page="dashboard">System</button>
    <button class="nav-btn" data-page="knowledge">Knowledge</button>
    <button class="nav-btn" data-page="workflows">Workflows</button>
  </div>

  <!-- Home / Avatar Page -->
  <div id="page-home" class="page active">
    <div class="avatar-container">
      <div class="avatar-face" id="avatar-face">
        <div class="avatar-ring"></div>
        <div class="avatar-ring-outer"></div>
        <div class="avatar-scanline"></div>
        <div class="avatar-particles">
          <div class="avatar-particle"></div>
          <div class="avatar-particle"></div>
          <div class="avatar-particle"></div>
          <div class="avatar-particle"></div>
          <div class="avatar-particle"></div>
          <div class="avatar-particle"></div>
        </div>
        <div class="avatar-brow">
          <div class="avatar-brow-line"></div>
          <div class="avatar-brow-line"></div>
        </div>
        <div class="avatar-eyes">
          <div class="eye" id="eye-left"><div class="iris"></div><div class="pupil"></div></div>
          <div class="eye" id="eye-right"><div class="iris"></div><div class="pupil"></div></div>
        </div>
        <div class="avatar-nose"></div>
        <div class="avatar-mouth" id="avatar-mouth"></div>
      </div>
      <div class="avatar-state-label" id="avatar-state-label">BOOTING</div>
      <div class="avatar-emotion-label" id="avatar-emotion-label">initializing systems...</div>
    </div>
    <div class="card">
      <h3>System Status</h3>
      <div id="home-status">Connecting to ELIOT...</div>
    </div>
  </div>

  <!-- Chat Page -->
  <div id="page-chat" class="page">
    <div class="chat-container">
      <div class="chat-messages" id="chat-messages">
        <div class="chat-msg agent">
          <div class="msg-sender">ELIOT CORE</div>
          System online. All agents operational. How can I assist you?
        </div>
      </div>
      <div class="chat-input-bar">
        <input id="chat-input" placeholder="Enter command or question..." autocomplete="off">
        <button id="chat-send" onclick="sendChat()">Send</button>
      </div>
    </div>
  </div>

  <!-- Dashboard Page -->
  <div id="page-dashboard" class="page">
    <div class="card">
      <h3>Hardware</h3>
      <div id="dash-hardware">Loading...</div>
    </div>
    <div class="card">
      <h3>Services</h3>
      <div id="dash-services">Loading...</div>
    </div>
    <div class="card">
      <h3>Agents</h3>
      <div id="dash-agents">Loading...</div>
    </div>
  </div>

  <!-- Knowledge Page -->
  <div id="page-knowledge" class="page">
    <div class="card">
      <h3>Knowledge Base</h3>
      <div id="kb-stats">Loading...</div>
    </div>
    <div class="card">
      <h3>Semantic Search</h3>
      <div class="kb-search">
        <input id="kb-input" placeholder="Search security knowledge..." onkeydown="if(event.key==='Enter')searchKB()">
        <button onclick="searchKB()">Search</button>
      </div>
      <div id="kb-results"></div>
    </div>
  </div>

  <!-- Workflows Page -->
  <div id="page-workflows" class="page">
    <div class="card">
      <h3>Multi-Agent Workflows</h3>
      <p style="color:#555;font-size:12px;margin-bottom:12px;">
        Execute coordinated security workflows across multiple agents.
      </p>
      <div id="workflows-list">Loading...</div>
    </div>
    <div class="card" id="wf-run-card" style="display:none">
      <h3>Workflow Output</h3>
      <div id="wf-output" style="font-size:12px;line-height:1.6;max-height:400px;overflow-y:auto;"></div>
    </div>
  </div>
</div>

<script>
// ── Boot Sequence ──
const BOOT_LINES = [
  '[BIOS] ELIOT Core v0.3.0 - Embedded Local Intelligence Operations Terminal',
  '[BOOT] Initializing hardware abstraction layer...',
  '[BOOT] NVIDIA Jetson Orin Nano detected',
  '[BOOT] CUDA 12.1 toolkit available',
  '[INIT] Loading agent framework...',
  '[INIT] 8 agents registered: Supervisor, Planner, Knowledge, Analysis, Research, Code, Documentation, Voice, Vision',
  '[INIT] Knowledge engine online - 57 documents indexed',
  '[INIT] Ollama GPU inference: qwen2.5:3b @ 22 tok/s',
  '[INIT] Connecting to ChromaDB vector store...',
  '[INIT] Redis message broker connected',
  '[WARN] Voice hardware not detected (expected on dev)',
  '[WARN] Vision hardware not detected (expected on dev)',
  '[SYS ] All critical systems operational',
  '[SYS ] Avatar engine initialized',
  '[SYS ] Ready.',
];

let bootIdx = 0;
let bootDone = false;
const bootText = document.getElementById('boot-text');
const bootProgress = document.getElementById('boot-progress');

function bootStep() {
  if (bootIdx >= BOOT_LINES.length) {
    bootDone = true;
    setTimeout(() => {
      document.getElementById('boot-screen').classList.add('hidden');
      document.getElementById('app').style.display = '';
      setTimeout(() => document.getElementById('boot-screen').remove(), 1000);
      initApp();
    }, 400);
    return;
  }
  bootText.innerHTML += BOOT_LINES[bootIdx] + '<br>';
  bootText.scrollTop = bootText.scrollHeight;
  bootProgress.style.width = ((bootIdx + 1) / BOOT_LINES.length * 100) + '%';
  bootIdx++;
  setTimeout(bootStep, 80 + Math.random() * 120);
}
setTimeout(bootStep, 500);

// ── Navigation ──
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('page-' + btn.dataset.page).classList.add('active');
    loadPageData(btn.dataset.page);
  });
});

// ── Avatar State ──
let avatarState = 'booting';
let avatarEmotion = 'neutral';
let ws = null;
let idleEyeTimer = null;

function connectAvatarWS() {
  const wsUrl = 'ws://' + location.host + '/avatar/ws';
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    console.log('Avatar WS connected');
    startIdleAnimations();
  };
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      updateAvatar(data);
    } catch(err) {}
  };
  ws.onclose = () => setTimeout(connectAvatarWS, 3000);
  ws.onerror = () => ws.close();
}

function startIdleAnimations() {
  if (idleEyeTimer) clearInterval(idleEyeTimer);
  idleEyeTimer = setInterval(() => {
    if (avatarState !== 'idle') return;
    const eyes = document.querySelectorAll('.eye');
    const dirs = ['look-left', 'look-right', 'look-up', 'look-down', ''];
    const dir = dirs[Math.floor(Math.random() * dirs.length)];
    eyes.forEach(e => {
      e.className = 'eye';
      if (dir) e.classList.add(dir);
    });
    setTimeout(() => eyes.forEach(e => e.className = 'eye'), 2000 + Math.random() * 2000);
  }, 4000 + Math.random() * 3000);
}

function updateAvatar(data) {
  avatarState = data.state || 'idle';
  avatarEmotion = data.emotion || 'neutral';

  const face = document.getElementById('avatar-face');
  const mouth = document.getElementById('avatar-mouth');
  const stateLabel = document.getElementById('avatar-state-label');
  const emotionLabel = document.getElementById('avatar-emotion-label');

  face.className = 'avatar-face';
  if (['thinking','analyzing'].includes(avatarState)) face.classList.add('state-thinking');
  if (avatarState === 'alert') face.classList.add('state-alert');
  if (['speaking','reporting'].includes(avatarState)) face.classList.add('state-speaking');

  mouth.className = 'avatar-mouth';
  if (['speaking','reporting'].includes(avatarState)) mouth.classList.add('speaking');
  else if (avatarEmotion === 'satisfied') mouth.classList.add('smile');
  else if (avatarEmotion === 'concerned') mouth.classList.add('frown');

  stateLabel.textContent = avatarState.toUpperCase();
  emotionLabel.textContent = data.text_display || avatarEmotion;

  const statusText = document.getElementById('status-text');
  if (statusText) statusText.textContent = avatarState.toUpperCase();
  
  if (avatarState === 'idle') startIdleAnimations();
}

// ── Chat ──
let chatHistory = [];

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  addChatMsg(msg, 'user');

  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({type:'set_state', state:'thinking'}));
  }

  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  document.getElementById('chat-messages').appendChild(typing);
  scrollChat();

  try {
    // Check if this is a shell command (starts with !)
    let endpoint = '/agents/chat';
    let body = {message: msg};
    
    if (msg.startsWith('!')) {
      // Route to shell agent
      endpoint = '/agents/chat';
      body = {message: msg, agent: 'Shell'};
    } else if (msg.toLowerCase().startsWith('launch ') || msg.toLowerCase().startsWith('open ')) {
      // Route to shell agent for app launching
      endpoint = '/agents/chat';
      body = {message: msg, agent: 'Shell'};
    } else if (msg.toLowerCase().startsWith('chain ')) {
      // Route to shell agent for event chaining
      endpoint = '/agents/chat';
      body = {message: msg, agent: 'Shell'};
    } else if (msg.toLowerCase().startsWith('analyze ') || msg.toLowerCase().startsWith('analyse ')) {
      // Route to shell agent for command analysis
      endpoint = '/agents/chat';
      body = {message: msg, agent: 'Shell'};
    }
    
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    typing.remove();
    
    // Handle command output specially
    if (d.message_type === 'command_output' || d.message_type === 'chain_output') {
      addCommandOutput(d.content, d.metadata);
    } else if (d.message_type === 'warning' && d.metadata?.requires_confirmation) {
      addConfirmationPrompt(d.content, d.metadata.command);
    } else {
      addChatMsg(d.content, 'agent', d.sender);
    }
    
    chatHistory.push({role:'user', content:msg}, {role:'assistant', content:d.content, sender:d.sender});

    if (ws && ws.readyState === 1) {
      ws.send(JSON.stringify({type:'set_state', state:'idle'}));
      ws.send(JSON.stringify({type:'set_text', text: d.sender + ': ' + d.content.substring(0,100)}));
    }
  } catch(e) {
    typing.remove();
    addChatMsg('Connection error. ELIOT core unreachable.', 'agent', 'SYSTEM');
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({type:'set_state', state:'idle'}));
  }
}

function addChatMsg(text, type, sender) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + type;
  const senderLabel = type === 'user' ? 'YOU' : (sender || 'ELIOT').toUpperCase();
  div.innerHTML = '<div class="msg-sender">' + senderLabel + '</div>' + escapeHtml(text);
  box.appendChild(div);
  scrollChat();
}

function addCommandOutput(text, metadata) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg agent';
  
  const command = metadata?.command || '';
  const returnCode = metadata?.return_code;
  
  let header = '<div class="msg-sender">SHELL</div>';
  header += '<div style="color:var(--cyan);font-size:11px;margin-bottom:8px;">$ ' + escapeHtml(command) + '</div>';
  
  if (returnCode !== undefined) {
    const color = returnCode === 0 ? 'var(--green)' : 'var(--red)';
    header += '<div style="color:' + color + ';font-size:10px;margin-bottom:8px;">Exit code: ' + returnCode + '</div>';
  }
  
  div.innerHTML = header + '<pre style="margin:0;white-space:pre-wrap;font-size:12px;line-height:1.4;">' + escapeHtml(text) + '</pre>';
  box.appendChild(div);
  scrollChat();
}

function addConfirmationPrompt(text, command) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg agent';
  div.style.borderColor = 'var(--orange)';
  
  let html = '<div class="msg-sender" style="color:var(--orange);">WARNING</div>';
  html += '<div style="color:var(--orange);margin-bottom:8px;">' + escapeHtml(text) + '</div>';
  html += '<div style="display:flex;gap:8px;margin-top:8px;">';
  html += '<button onclick="confirmCommand(\'' + escapeHtml(command) + '\')" style="background:var(--red);color:#000;border:none;padding:6px 12px;cursor:pointer;font-weight:bold;">Confirm</button>';
  html += '<button onclick="cancelCommand()" style="background:#333;color:#fff;border:none;padding:6px 12px;cursor:pointer;">Cancel</button>';
  html += '</div>';
  
  div.innerHTML = html;
  box.appendChild(div);
  scrollChat();
}

function confirmCommand(command) {
  document.getElementById('chat-input').value = 'confirm ' + command;
  sendChat();
}

function cancelCommand() {
  document.getElementById('chat-input').value = 'cancel';
  sendChat();
}

function scrollChat() {
  const box = document.getElementById('chat-messages');
  requestAnimationFrame(() => box.scrollTop = box.scrollHeight);
}

function escapeHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendChat();
});

// ── Dashboard ──
async function loadDashboard() {
  try {
    const r = await fetch('/system/info');
    const d = await r.json();
    const totalMem = (d.hardware.memory_gb || 0).toFixed(1);
    const usedMem = ((d.hardware.memory_gb || 0) - (d.metrics.memory_available_gb || 0)).toFixed(1);
    document.getElementById('dash-hardware').innerHTML = `
      <div class="metric-row"><span class="metric-label">Target</span><span class="metric-value">${d.hardware.target}</span></div>
      <div class="metric-row"><span class="metric-label">CPU</span><span class="metric-value">${d.metrics.cpu_percent}%</span></div>
      <div class="metric-row"><span class="metric-label">Memory</span><span class="metric-value">${d.metrics.memory_percent}% (${usedMem}GB / ${totalMem}GB)</span></div>
      <div class="metric-row"><span class="metric-label">Disk</span><span class="metric-value">${d.metrics.disk_percent}%</span></div>
      <div class="metric-row"><span class="metric-label">CUDA</span><span class="metric-value">${d.hardware.cuda_available ? 'Available' : 'N/A'}</span></div>
    `;
  } catch(e) {
    document.getElementById('dash-hardware').innerHTML = '<span style="color:#555">Unable to fetch hardware info</span>';
  }

  try {
    const r = await fetch('/health/detailed');
    const d = await r.json();
    let svcHtml = '';
    for (const [k,v] of Object.entries(d.services || {})) {
      svcHtml += `<div class="metric-row"><span class="metric-label">${k}</span><span class="metric-value" style="color:${v==='healthy'?'var(--green)':'var(--red)'}">${v}</span></div>`;
    }
    document.getElementById('dash-services').innerHTML = svcHtml || '<span style="color:#555">No service data</span>';
  } catch(e) {}

  try {
    const r = await fetch('/agents/');
    const agents = await r.json();
    let agentHtml = '';
    agents.forEach(a => {
      agentHtml += `<div class="metric-row"><span class="metric-label">${a.name}</span><span class="metric-value">${a.tasks_completed} tasks | ${a.errors} errors | ${a.state}</span></div>`;
    });
    document.getElementById('dash-agents').innerHTML = agentHtml;
  } catch(e) {}
}

// ── Knowledge ──
async function loadKnowledge() {
  try {
    const r = await fetch('/knowledge/stats');
    const d = await r.json();
    document.getElementById('kb-stats').innerHTML = `
      <div class="metric-row"><span class="metric-label">Documents</span><span class="metric-value">${d.total_documents}</span></div>
      <div class="metric-row"><span class="metric-label">Embedding Dimensions</span><span class="metric-value">${d.embedding_dimensions}</span></div>
      <div class="metric-row"><span class="metric-label">Total Ingested</span><span class="metric-value">${d.total_ingested}</span></div>
    `;
  } catch(e) {
    document.getElementById('kb-stats').innerHTML = '<span style="color:#555">Knowledge engine unavailable</span>';
  }
}

async function searchKB() {
  const q = document.getElementById('kb-input').value.trim();
  if (!q) return;
  const box = document.getElementById('kb-results');
  box.innerHTML = '<span style="color:#555">Searching...</span>';
  try {
    const r = await fetch('/knowledge/search?q=' + encodeURIComponent(q));
    const d = await r.json();
    if (!d.results || d.results.length === 0) {
      box.innerHTML = '<span style="color:#555">No results found</span>';
      return;
    }
    box.innerHTML = d.results.map(r => `
      <div class="kb-result">
        <span class="kb-source">${r.source || 'unknown'}</span>
        <span class="kb-score">score: ${(r.score||0).toFixed(3)}</span>
        <div class="kb-text">${escapeHtml((r.text||'').substring(0, 300))}...</div>
      </div>
    `).join('');
  } catch(e) {
    box.innerHTML = '<span style="color:var(--red)">Search failed</span>';
  }
}

// ── Workflows ──
async function loadWorkflows() {
  try {
    const r = await fetch('/agents/workflows/list');
    const d = await r.json();
    const box = document.getElementById('workflows-list');
    let html = '';
    for (const [name, wf] of Object.entries(d.workflows || {})) {
      html += `
        <div class="workflow-card" onclick="runWorkflow('${name}')">
          <h4>${name}</h4>
          <p>${wf.description || ''}</p>
          <div class="wf-agents">
            ${(wf.agents || []).map(a => '<span class="wf-agent-tag">'+a+'</span>').join('')}
          </div>
        </div>
      `;
    }
    box.innerHTML = html || '<span style="color:#555">No workflows defined</span>';
  } catch(e) {
    document.getElementById('workflows-list').innerHTML = '<span style="color:#555">Unable to load workflows</span>';
  }
}

async function runWorkflow(name) {
  const card = document.getElementById('wf-run-card');
  const output = document.getElementById('wf-output');
  card.style.display = '';
  output.innerHTML = '<span style="color:var(--cyan)">Running workflow: ' + name + '...</span>';

  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({type:'set_state', state:'thinking'}));
  }

  try {
    const prompt = prompt_for_workflow(name);
    const r = await fetch('/agents/workflow/' + name, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: prompt})
    });
    const d = await r.json();
    output.innerHTML = '<div style="color:var(--green);margin-bottom:8px;">Workflow complete.</div>' +
      '<div style="color:var(--cyan);font-size:10px;margin-bottom:8px;">Agent: ' + d.sender + '</div>' +
      '<div>' + escapeHtml(d.content) + '</div>';
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({type:'set_state', state:'idle'}));
  } catch(e) {
    output.innerHTML = '<span style="color:var(--red)">Workflow timed out or failed. Workflows with many agents may take several minutes.</span>';
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({type:'set_state', state:'idle'}));
  }
}

function prompt_for_workflow(name) {
  const prompts = {
    recon: 'Perform reconnaissance analysis on common network security posture',
    vuln_assessment: 'Assess vulnerability risks of running outdated OpenSSL versions',
    incident_response: 'Analyze indicators of compromise for a phishing attack scenario',
    pentest: 'Plan a penetration test for a web application with login functionality',
  };
  return prompts[name] || 'Execute workflow';
}

// ── Home Status ──
async function loadHomeStatus() {
  try {
    const r = await fetch('/health/detailed');
    const d = await r.json();
    document.getElementById('home-status').innerHTML = `
      <div class="metric-row"><span class="metric-label">Version</span><span class="metric-value">${d.version}</span></div>
      <div class="metric-row"><span class="metric-label">Status</span><span class="metric-value" style="color:var(--green)">${d.status}</span></div>
      <div class="metric-row"><span class="metric-label">Uptime</span><span class="metric-value">${formatUptime(d.uptime_seconds)}</span></div>
    `;
    document.getElementById('status-text').textContent = avatarState.toUpperCase();
  } catch(e) {}
}

function formatUptime(s) {
  if (!s) return 'N/A';
  const h = Math.floor(s/3600);
  const m = Math.floor((s%3600)/60);
  return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
}

function loadPageData(name) {
  if (name === 'dashboard') loadDashboard();
  if (name === 'knowledge') loadKnowledge();
  if (name === 'workflows') loadWorkflows();
  if (name === 'home') loadHomeStatus();
}

// ── Init ──
function initApp() {
  connectAvatarWS();
  loadHomeStatus();
  setInterval(loadHomeStatus, 15000);
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def ui_home():
    return HTML_TEMPLATE
