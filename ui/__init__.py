"""
ELIOT Touch UI v2

Cyberpunk interface with Mr. Robot tamagotchi avatar,
interactive network topology, prompt suggestions, workflow forms,
tamagotchi notifications, and knowledge dashboard.
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
<title>ELIOT — Embedded Local Intelligence Operations Terminal</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700&display=swap');

:root {
  --green: #00ff41; --green-dim: #00cc33; --green-glow: rgba(0,255,65,0.3);
  --orange: #ff6600; --red: #ff0040; --cyan: #00e5ff;
  --bg: #050508; --panel: #0a0a0f; --border: #1a1a2e; --text: #c0c0c0;
}

* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; overflow:hidden; }
body { font-family:'Share Tech Mono','Courier New',monospace; background:var(--bg); color:var(--text); }

body::after {
  content:''; position:fixed; inset:0; z-index:9999;
  background: repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.06) 2px,rgba(0,0,0,0.06) 4px);
  pointer-events:none;
}

/* ── Header ── */
.header {
  height:44px; background:linear-gradient(180deg,#0d0d14,#080810);
  border-bottom:1px solid var(--border); display:flex; align-items:center;
  justify-content:space-between; padding:0 16px; position:relative;
}
.header::after { content:''; position:absolute; bottom:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,var(--green),transparent); opacity:0.5; }
.logo { font-family:'Orbitron',monospace; font-size:18px; font-weight:700; color:var(--green); text-shadow:0 0 10px var(--green-glow); letter-spacing:3px; }
.header-right { display:flex; align-items:center; gap:12px; font-size:11px; }
.stealth-badge { padding:2px 8px; border:1px solid var(--green); color:var(--green); font-size:9px; text-transform:uppercase; letter-spacing:1px; }
.stealth-badge.off { border-color:var(--red); color:var(--red); }
.status-dot { width:6px; height:6px; border-radius:50%; background:var(--green); box-shadow:0 0 6px var(--green); animation:pulse-dot 2s infinite; }
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* ── Nav ── */
.nav {
  height:36px; display:flex; gap:2px; padding:0 8px;
  background:var(--panel); border-bottom:1px solid var(--border); align-items:center;
}
.nav-btn {
  background:transparent; border:1px solid transparent; color:#555;
  padding:5px 12px; font-family:inherit; font-size:11px; cursor:pointer;
  text-transform:uppercase; letter-spacing:1px; transition:all 0.2s; position:relative;
}
.nav-btn:hover { color:var(--green); border-color:#1a1a2e; }
.nav-btn.active { color:var(--green); border-color:var(--green); background:rgba(0,255,65,0.05); text-shadow:0 0 8px var(--green-glow); }
.nav-btn.active::after { content:''; position:absolute; bottom:-1px; left:20%; right:20%; height:1px; background:var(--green); }
.nav-badge { background:var(--red); color:#fff; font-size:8px; padding:1px 4px; border-radius:6px; margin-left:4px; }

/* ── Pages ── */
.page { display:none; height:calc(100vh - 80px); overflow-y:auto; padding:12px; animation:fadeIn 0.3s ease; }
.page.active { display:block; }
@keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
::-webkit-scrollbar { width:4px; } ::-webkit-scrollbar-track { background:var(--bg); } ::-webkit-scrollbar-thumb { background:#1a1a2e; border-radius:2px; }

/* ── Cards ── */
.card {
  background:var(--panel); border:1px solid var(--border); padding:14px;
  margin-bottom:10px; position:relative; overflow:hidden;
}
.card::before { content:''; position:absolute; top:0; left:0; width:3px; height:100%; background:var(--green); opacity:0.6; }
.card h3 { font-family:'Orbitron',monospace; font-size:10px; color:var(--green); text-transform:uppercase; letter-spacing:2px; margin-bottom:10px; display:flex; align-items:center; gap:8px; }
.card h3::before { content:'>'; color:var(--green); }
.metric-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #0d0d14; font-size:12px; }
.metric-row:last-child { border-bottom:none; }
.metric-label { color:#555; }
.metric-value { color:var(--green); font-weight:bold; }
.metric-bar { height:3px; background:#111; border-radius:2px; margin-top:3px; overflow:hidden; }
.metric-bar-fill { height:100%; border-radius:2px; background:linear-gradient(90deg,var(--green-dim),var(--green)); transition:width 0.5s; box-shadow:0 0 6px var(--green-glow); }

/* ── Mr. Robot Avatar ── */
.tama-container { display:flex; flex-direction:column; align-items:center; padding:16px 0; }
.robot-frame {
  width:280px; height:320px; position:relative;
  border:1px solid var(--border); background:#060610;
  overflow:hidden; transition:all 0.5s;
}
.robot-frame.scanning { border-color:var(--cyan); box-shadow:0 0 40px rgba(0,229,255,0.15); }
.robot-frame.alert { border-color:var(--red); box-shadow:0 0 50px rgba(255,0,64,0.2); animation:alert-pulse 0.8s infinite; }
.robot-frame.exploiting { border-color:var(--orange); box-shadow:0 0 40px rgba(255,102,0,0.2); }
.robot-frame.cracking { border-color:#ff00ff; box-shadow:0 0 40px rgba(255,0,255,0.15); }
@keyframes alert-pulse { 0%,100%{box-shadow:0 0 50px rgba(255,0,64,0.2)} 50%{box-shadow:0 0 70px rgba(255,0,64,0.35)} }

/* ASCII Robot Art */
.robot-ascii {
  position:absolute; inset:8px; font-family:'Share Tech Mono',monospace;
  font-size:11px; line-height:1.2; color:var(--green); white-space:pre;
  opacity:0.9; text-shadow:0 0 8px var(--green-glow);
}
.robot-ascii .eyes { animation:eye-flicker 4s ease-in-out infinite; }
@keyframes eye-flicker { 0%,90%,100%{opacity:1} 92%{opacity:0.2} 94%{opacity:1} 96%{opacity:0.3} }

/* Scan line over robot */
.robot-scanline {
  position:absolute; left:0; right:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(0,229,255,0.4),transparent);
  animation:robot-scan 3s ease-in-out infinite; pointer-events:none; z-index:2;
}
@keyframes robot-scan { 0%{top:5%;opacity:0} 10%{opacity:1} 90%{opacity:1} 100%{top:95%;opacity:0} }

/* Typing effect overlay */
.robot-typing {
  position:absolute; bottom:8px; left:8px; right:8px;
  font-size:10px; color:var(--green); opacity:0.7;
  border-top:1px solid rgba(0,255,65,0.1); padding-top:4px;
  max-height:60px; overflow:hidden;
}
.robot-typing .cursor { animation:cursor-blink 0.6s infinite; }
@keyframes cursor-blink { 0%,100%{opacity:1} 50%{opacity:0} }

/* Matrix rain background */
.matrix-bg {
  position:absolute; inset:0; overflow:hidden; opacity:0.04; pointer-events:none;
}
.matrix-col {
  position:absolute; top:-100%; font-family:'Share Tech Mono',monospace;
  font-size:10px; color:var(--green); animation:matrix-fall linear infinite;
  white-space:nowrap;
}
@keyframes matrix-fall { 0%{transform:translateY(-100%)} 100%{transform:translateY(400%)} }

.tama-state { margin-top:12px; font-family:'Orbitron',monospace; font-size:12px; color:var(--green); text-transform:uppercase; letter-spacing:3px; text-shadow:0 0 10px var(--green-glow); }
.tama-detail { margin-top:4px; font-size:10px; color:#555; }

/* ── Chat ── */
.chat-container { display:flex; flex-direction:column; height:calc(100vh - 92px); }
.chat-messages { flex:1; overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:6px; }
.chat-msg { max-width:80%; padding:8px 12px; font-size:12px; line-height:1.5; border-radius:2px; animation:msg-in 0.2s ease; word-wrap:break-word; white-space:pre-wrap; }
@keyframes msg-in { from{opacity:0;transform:translateY(6px)} }
.chat-msg.user { align-self:flex-end; background:rgba(255,102,0,0.1); border:1px solid rgba(255,102,0,0.3); color:var(--orange); }
.chat-msg.agent { align-self:flex-start; background:rgba(0,255,65,0.05); border:1px solid rgba(0,255,65,0.2); color:var(--text); }
.msg-sender { font-family:'Orbitron',monospace; font-size:8px; text-transform:uppercase; letter-spacing:1px; margin-bottom:3px; opacity:0.6; }
.chat-msg.user .msg-sender { color:var(--orange); }
.chat-msg.agent .msg-sender { color:var(--green); }

.typing-indicator { display:flex; gap:4px; padding:8px 12px; align-self:flex-start; background:rgba(0,255,65,0.05); border:1px solid rgba(0,255,65,0.2); border-radius:2px; }
.typing-dot { width:5px; height:5px; border-radius:50%; background:var(--green); opacity:0.4; animation:typing-bounce 1.2s infinite; }
.typing-dot:nth-child(2){animation-delay:0.2s} .typing-dot:nth-child(3){animation-delay:0.4s}
@keyframes typing-bounce { 0%,60%,100%{opacity:0.4;transform:translateY(0)} 30%{opacity:1;transform:translateY(-3px)} }

.chat-input-bar { display:flex; gap:6px; padding:10px; background:var(--panel); border-top:1px solid var(--border); }
.chat-input-bar input { flex:1; background:#0a0a0f; border:1px solid var(--border); color:var(--green); padding:8px 12px; font-family:inherit; font-size:12px; outline:none; transition:border-color 0.2s; }
.chat-input-bar input:focus { border-color:var(--green); }
.chat-input-bar input::placeholder { color:#333; }
.chat-input-bar button { background:var(--green); color:#000; border:none; padding:8px 16px; font-family:inherit; font-size:11px; font-weight:bold; cursor:pointer; text-transform:uppercase; letter-spacing:1px; }

/* Prompt Suggestions */
.suggestions { display:flex; gap:4px; padding:6px 10px; overflow-x:auto; flex-wrap:nowrap; }
.suggestions::-webkit-scrollbar { height:2px; }
.suggest-chip {
  flex-shrink:0; padding:4px 10px; font-size:10px; border:1px solid var(--border);
  color:#666; cursor:pointer; transition:all 0.2s; white-space:nowrap;
  background:var(--panel);
}
.suggest-chip:hover { border-color:var(--green); color:var(--green); background:rgba(0,255,65,0.05); }

/* ── Network Map ── */
.network-map { width:100%; height:400px; background:#060610; border:1px solid var(--border); position:relative; overflow:hidden; margin-bottom:10px; }
.network-map svg { width:100%; height:100%; }
.net-node { cursor:pointer; transition:all 0.3s; }
.net-node:hover { filter:brightness(1.3); }
.net-node text { font-family:'Share Tech Mono',monospace; font-size:9px; fill:var(--text); }
.net-edge { stroke:#1a1a2e; stroke-width:1; }
.net-edge.active { stroke:var(--green); stroke-width:1.5; stroke-dasharray:4; animation:dash-flow 2s linear infinite; }
@keyframes dash-flow { to{stroke-dashoffset:-8} }

/* ── Notifications ── */
.notif-list { max-height:300px; overflow-y:auto; }
.notif-item {
  padding:8px 10px; border:1px solid var(--border); margin-bottom:6px;
  font-size:11px; display:flex; justify-content:space-between; align-items:center;
}
.notif-item.pending { border-left:3px solid var(--orange); }
.notif-item.approved { border-left:3px solid var(--green); }
.notif-item.denied { border-left:3px solid var(--red); }
.notif-title { color:var(--text); font-weight:bold; }
.notif-meta { color:#555; font-size:9px; }
.notif-actions { display:flex; gap:4px; }
.notif-btn { padding:3px 8px; font-size:9px; border:none; cursor:pointer; font-weight:bold; text-transform:uppercase; }
.notif-btn.approve { background:var(--green); color:#000; }
.notif-btn.deny { background:var(--red); color:#fff; }

/* ── Workflow Forms ── */
.workflow-card {
  background:var(--panel); border:1px solid var(--border); padding:12px;
  margin-bottom:8px; cursor:pointer; transition:all 0.2s;
}
.workflow-card:hover { border-color:var(--green); background:rgba(0,255,65,0.03); }
.workflow-card h4 { color:var(--green); font-size:12px; margin-bottom:3px; font-family:'Orbitron',monospace; text-transform:uppercase; letter-spacing:1px; }
.workflow-card p { color:#555; font-size:10px; }
.wf-form { margin-top:8px; display:none; }
.workflow-card.expanded .wf-form { display:block; }
.wf-form input, .wf-form select {
  width:100%; background:#0a0a0f; border:1px solid var(--border); color:var(--green);
  padding:6px 10px; font-family:inherit; font-size:11px; outline:none; margin-bottom:6px;
}
.wf-form input:focus, .wf-form select:focus { border-color:var(--green); }
.wf-form label { display:block; font-size:9px; color:#555; text-transform:uppercase; letter-spacing:1px; margin-bottom:2px; }
.wf-run-btn { background:var(--green); color:#000; border:none; padding:6px 14px; font-family:inherit; font-size:10px; font-weight:bold; cursor:pointer; text-transform:uppercase; }
.wf-agents { display:flex; gap:3px; margin-top:6px; flex-wrap:wrap; }
.wf-agent-tag { background:rgba(0,255,65,0.1); border:1px solid rgba(0,255,65,0.2); color:var(--green); padding:1px 6px; font-size:8px; text-transform:uppercase; letter-spacing:1px; }

/* ── Boot ── */
.boot-screen { position:fixed; inset:0; z-index:10000; background:var(--bg); display:flex; flex-direction:column; align-items:center; justify-content:center; transition:opacity 0.8s; }
.boot-screen.hidden { opacity:0; pointer-events:none; }
.boot-text { font-family:'Share Tech Mono',monospace; color:var(--green); font-size:13px; text-align:left; line-height:1.7; max-width:500px; }
.boot-progress { width:300px; height:2px; background:#111; margin-top:20px; border-radius:1px; overflow:hidden; }
.boot-progress-fill { height:100%; width:0%; background:var(--green); transition:width 0.3s; box-shadow:0 0 8px var(--green-glow); }

/* ── Two-col layout ── */
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
@media(max-width:768px){ .two-col{grid-template-columns:1fr} }
</style>
</head>
<body>

<div class="boot-screen" id="boot-screen">
  <div class="boot-text" id="boot-text"></div>
  <div class="boot-progress"><div class="boot-progress-fill" id="boot-progress"></div></div>
</div>

<div id="app" style="display:none">
  <div class="header">
    <div class="logo">ELIOT</div>
    <div class="header-right">
      <span class="stealth-badge" id="stealth-badge">STEALTH</span>
      <div class="status-dot"></div>
      <span id="tama-state-header">IDLE</span>
    </div>
  </div>
  <div class="nav">
    <button class="nav-btn active" data-page="home">Terminal</button>
    <button class="nav-btn" data-page="network">Network</button>
    <button class="nav-btn" data-page="chat">Chat</button>
    <button class="nav-btn" data-page="workflows">Workflows</button>
    <button class="nav-btn" data-page="tamagotchi">Tamagotchi<span class="nav-badge" id="notif-badge" style="display:none">0</span></button>
    <button class="nav-btn" data-page="system">System</button>
  </div>

  <!-- ── Home / Mr. Robot ── -->
  <div id="page-home" class="page active">
    <div class="tama-container">
      <div class="robot-frame" id="robot-frame">
        <div class="matrix-bg" id="matrix-bg"></div>
        <div class="robot-scanline"></div>
        <div class="robot-ascii" id="robot-art"></div>
        <div class="robot-typing" id="robot-typing"></div>
      </div>
      <div class="tama-state" id="tama-state">IDLE</div>
      <div class="tama-detail" id="tama-detail">systems online</div>
    </div>
    <div class="two-col">
      <div class="card">
        <h3>Quick Actions</h3>
        <div id="quick-actions"></div>
      </div>
      <div class="card">
        <h3>Recent Activity</h3>
        <div id="recent-activity" style="max-height:150px;overflow-y:auto;font-size:11px;">Loading...</div>
      </div>
    </div>
  </div>

  <!-- ── Network ── -->
  <div id="page-network" class="page">
    <div class="card">
      <h3>Network Topology</h3>
      <div class="network-map" id="network-map">
        <svg id="net-svg"></svg>
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button onclick="triggerScan()" style="background:var(--green);color:#000;border:none;padding:6px 14px;font-family:inherit;font-size:10px;font-weight:bold;cursor:pointer;text-transform:uppercase;">Scan Now</button>
        <span id="scan-status" style="color:#555;font-size:10px;line-height:28px;"></span>
      </div>
    </div>
    <div class="two-col">
      <div class="card">
        <h3>Discovered Devices</h3>
        <div id="device-list" style="max-height:300px;overflow-y:auto;">No devices yet</div>
      </div>
      <div class="card">
        <h3>WiFi Access Points</h3>
        <div id="wifi-list" style="max-height:300px;overflow-y:auto;">No APs found</div>
      </div>
    </div>
  </div>

  <!-- ── Chat ── -->
  <div id="page-chat" class="page">
    <div class="chat-container">
      <div class="chat-messages" id="chat-messages">
        <div class="chat-msg agent"><div class="msg-sender">ELIOT</div>System online. All agents operational. How can I assist you?</div>
      </div>
      <div class="suggestions" id="chat-suggestions"></div>
      <div class="chat-input-bar">
        <input id="chat-input" placeholder="Enter command or question..." autocomplete="off">
        <button id="chat-send" onclick="sendChat()">Send</button>
      </div>
    </div>
  </div>

  <!-- ── Workflows ── -->
  <div id="page-workflows" class="page">
    <div class="card">
      <h3>Workflows</h3>
      <p style="color:#555;font-size:11px;margin-bottom:10px;">Configure and execute multi-agent security workflows.</p>
      <div id="workflows-list">Loading...</div>
    </div>
    <div class="card">
      <h3>Quick Pentest</h3>
      <div style="display:flex;gap:6px;">
        <input id="pentest-target" placeholder="Target IP or CIDR" style="flex:1;background:#0a0a0f;border:1px solid var(--border);color:var(--green);padding:8px 12px;font-family:inherit;font-size:12px;outline:none;" onkeydown="if(event.key==='Enter')runPentest()">
        <button onclick="runPentest()" style="background:var(--red);color:#000;border:none;padding:8px 16px;font-family:inherit;font-size:11px;font-weight:bold;cursor:pointer;text-transform:uppercase;">Pentest</button>
      </div>
    </div>
    <div class="card" id="wf-run-card" style="display:none">
      <h3>Output</h3>
      <div id="wf-output" style="font-size:11px;line-height:1.5;max-height:500px;overflow-y:auto;"></div>
    </div>
  </div>

  <!-- ── Tamagotchi ── -->
  <div id="page-tamagotchi" class="page">
    <div class="two-col">
      <div class="card">
        <h3>Notifications</h3>
        <div class="notif-list" id="notif-list">Loading...</div>
      </div>
      <div class="card">
        <h3>Exploit Queue</h3>
        <div id="exploit-queue" style="max-height:300px;overflow-y:auto;">No exploits queued</div>
      </div>
    </div>
    <div class="card">
      <h3>Knowledge Base</h3>
      <div id="knowledge-stats" style="margin-bottom:8px;">Loading...</div>
      <div id="knowledge-entries" style="max-height:200px;overflow-y:auto;font-size:11px;"></div>
    </div>
    <div class="card">
      <h3>Cracking Sessions</h3>
      <div id="crack-sessions">No active sessions</div>
    </div>
  </div>

  <!-- ── System ── -->
  <div id="page-system" class="page">
    <div class="card"><h3>Hardware</h3><div id="dash-hardware">Loading...</div></div>
    <div class="card"><h3>Services</h3><div id="dash-services">Loading...</div></div>
    <div class="card"><h3>Agents</h3><div id="dash-agents">Loading...</div></div>
  </div>
</div>

<script>
// ═══════════════════════════════════════════════════
// Mr. Robot ASCII Art Frames
// ═══════════════════════════════════════════════════
const ROBOT_FRAMES = {
idle: `       ┌─────────────────┐
       │  ░░░░░░░░░░░░░  │
       │  ░ ┌─────────┐ ░  │
       │  ░ │ ▓▓   ▓▓ │ ░  │
       │  ░ │ ▓▓   ▓▓ │ ░  │
       │  ░ │  ╲   ╱  │ ░  │
       │  ░ └─────────┘ ░  │
       │  ░░░░░░░░░░░░░  │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║    ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │   ╱          ╲   │
       └─────────────────┘`,
scanning: `       ┌─────────────────┐
       │  ▓▓▓▓▓▓▓▓▓▓▓▓▓  │
       │  ▓ ┌─────────┐ ▓  │
       │  ▓ │ ◉◉   ◉◉ │ ▓  │
       │  ▓ │ ◉◉   ◉◉ │ ▓  │
       │  ▓ │  ◇   ◇  │ ▓  │
       │  ▓ └─────────┘ ▓  │
       │  ▓▓▓▓▓▓▓▓▓▓▓▓▓  │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║ ◊◊ ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │   ╱   ◈◈◈   ╲   │
       └─────────────────┘`,
alert: `       ┌─────────────────┐
       │  █████████████  │
       │  █ ┌─────────┐ █  │
       │  █ │ ▓▓▓  ▓▓▓│ █  │
       │  █ │ ▓▓▓  ▓▓▓│ █  │
       │  █ │  ▲   ▲  │ █  │
       │  █ └─────────┘ █  │
       │  █████████████  │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║ ⚠⚠ ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │   ╱  ▓▓▓▓▓▓  ╲  │
       └─────────────────┘`,
exploiting: `       ┌─────────────────┐
       │  ▒▒▒▒▒▒▒▒▒▒▒▒▒  │
       │  ▒ ┌─────────┐ ▒  │
       │  ▒ │ ██   ██ │ ▒  │
       │  ▒ │ ██   ██ │ ▒  │
       │  ▒ │  ▓   ▓  │ ▒  │
       │  ▒ └─────────┘ ▒  │
       │  ▒▒▒▒▒▒▒▒▒▒▒▒▒  │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║ >> ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │   ╱  ▶▶▶▶▶▶  ╲  │
       └─────────────────┘`,
cracking: `       ┌─────────────────┐
       │  ░░░░░░░░░░░░░  │
       │  ░ ┌─────────┐ ░  │
       │  ░ │ ◆◆   ◆◆ │ ░  │
       │  ░ │ ◆◆   ◆◆ │ ░  │
       │  ░ │  ♦   ♦  │ ░  │
       │  ░ └─────────┘ ░  │
       │  ░░░░░░░░░░░░░  │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║$$$ ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │   ╱  $$$$$$$  ╲  │
       └─────────────────┘`,
analyzing: `       ┌─────────────────┐
       │  ═════════════  │
       │  ═ ┌─────────┐ ═  │
       │  ═ │ ●●   ●● │ ═  │
       │  ═ │ ●●   ●● │ ═  │
       │  ═ │  ○   ○  │ ═  │
       │  ═ └─────────┘ ═  │
       │  ═════════════  │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║ ◎◎ ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │   ╱  ≡≡≡≡≡≡  ╲  │
       └─────────────────┘`,
sleeping: `       ┌─────────────────┐
       │                   │
       │    ┌─────────┐    │
       │    │ ──   ── │    │
       │    │         │    │
       │    │  ─   ─  │    │
       │    └─────────┘    │
       │                   │
       │    ┌────────┐    │
       │    │ ╔════╗ │    │
       │    │ ║    ║ │    │
       │    │ ╚════╝ │    │
       │    └────────┘    │
       │    z  Z  z  Z    │
       └─────────────────┘`
};

// ═══════════════════════════════════════════════════
// Boot Sequence
// ═══════════════════════════════════════════════════
const BOOT_LINES = [
  '[BIOS] ELIOT Core v0.4.0 — Embedded Local Intelligence Operations Terminal',
  '[BOOT] Initializing hardware abstraction...',
  '[BOOT] NVIDIA Jetson Orin Nano detected',
  '[BOOT] CUDA 12.1 available — GPU inference ready',
  '[INIT] Loading agent framework...',
  '[INIT] 9 agents registered + Stealth + Sentient + Tamagotchi',
  '[INIT] Knowledge engine online — security KB indexed',
  '[INIT] Ollama GPU: qwen2.5:3b @ 22 tok/s',
  '[INIT] Stealth engine: ACTIVE (profile: normal)',
  '[INIT] Sentient engine: autonomous scanning enabled',
  '[INIT] Tamagotchi engine: autonomous intelligence active',
  '[SYS ] All systems operational',
  '[SYS ] Mr. Robot avatar initialized',
  '[SYS ] Ready.',
];
let bootIdx = 0;
const bootText = document.getElementById('boot-text');
const bootProgress = document.getElementById('boot-progress');
function bootStep() {
  if (bootIdx >= BOOT_LINES.length) {
    setTimeout(() => {
      document.getElementById('boot-screen').classList.add('hidden');
      document.getElementById('app').style.display = '';
      setTimeout(() => document.getElementById('boot-screen').remove(), 1000);
      initApp();
    }, 300);
    return;
  }
  bootText.innerHTML += BOOT_LINES[bootIdx] + '<br>';
  bootText.scrollTop = bootText.scrollHeight;
  bootProgress.style.width = ((bootIdx+1)/BOOT_LINES.length*100)+'%';
  bootIdx++;
  setTimeout(bootStep, 70+Math.random()*100);
}
setTimeout(bootStep, 400);

// ═══════════════════════════════════════════════════
// Navigation
// ═══════════════════════════════════════════════════
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('page-'+btn.dataset.page).classList.add('active');
    loadPageData(btn.dataset.page);
  });
});

// ═══════════════════════════════════════════════════
// Matrix Rain Background
// ═══════════════════════════════════════════════════
function initMatrix() {
  const bg = document.getElementById('matrix-bg');
  if (!bg) return;
  bg.innerHTML = '';
  const chars = '01アイウエオカキクケコサシスセソ';
  for (let i = 0; i < 15; i++) {
    const col = document.createElement('div');
    col.className = 'matrix-col';
    col.style.left = (i/15*100)+'%';
    col.style.animationDuration = (3+Math.random()*4)+'s';
    col.style.animationDelay = (-Math.random()*5)+'s';
    let text = '';
    for (let j=0;j<20;j++) text += chars[Math.floor(Math.random()*chars.length)]+'\n';
    col.textContent = text;
    bg.appendChild(col);
  }
}

// ═══════════════════════════════════════════════════
// Mr. Robot Avatar
// ═══════════════════════════════════════════════════
let tamaState = 'idle';
let tamaDetail = 'systems online';
let typingText = '';
let typingIdx = 0;

function updateRobot(state, detail) {
  tamaState = state || 'idle';
  tamaDetail = detail || tamaDetail;
  const frame = document.getElementById('robot-frame');
  const art = document.getElementById('robot-art');
  const stateEl = document.getElementById('tama-state');
  const detailEl = document.getElementById('tama-detail');
  const headerState = document.getElementById('tama-state-header');

  art.innerHTML = ROBOT_FRAMES[tamaState] || ROBOT_FRAMES.idle;
  stateEl.textContent = tamaState.toUpperCase();
  detailEl.textContent = tamaDetail;
  if (headerState) headerState.textContent = tamaState.toUpperCase();

  frame.className = 'robot-frame';
  if (['scanning','mapping'].includes(tamaState)) frame.classList.add('scanning');
  else if (tamaState === 'alert') frame.classList.add('alert');
  else if (tamaState === 'exploiting') frame.classList.add('exploiting');
  else if (tamaState === 'cracking') frame.classList.add('cracking');
}

function setTypingText(text) {
  typingText = text || '';
  typingIdx = 0;
}

setInterval(() => {
  const el = document.getElementById('robot-typing');
  if (!el || !typingText) return;
  typingIdx = (typingIdx + 1) % (typingText.length + 10);
  const visible = typingText.substring(0, typingIdx);
  el.innerHTML = 'root@eliot:~$ ' + visible + '<span class="cursor">█</span>';
}, 60);

// ═══════════════════════════════════════════════════
// WebSocket — Avatar + Tamagotchi
// ═══════════════════════════════════════════════════
let ws = null;
function connectWS() {
  ws = new WebSocket('ws://'+location.host+'/avatar/ws');
  ws.onopen = () => {
    setTimeout(() => {
      if (tamaState === 'idle') updateRobot('idle','systems online');
    }, 3000);
  };
  ws.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data);
      updateRobot(d.state, d.text_display || d.emotion);
    } catch(err){}
  };
  ws.onclose = () => setTimeout(connectWS, 3000);
  ws.onerror = () => ws.close();
}

// ═══════════════════════════════════════════════════
// Chat
// ═══════════════════════════════════════════════════
async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  addChatMsg(msg, 'user');
  if (ws && ws.readyState===1) ws.send(JSON.stringify({type:'set_state',state:'thinking'}));

  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  document.getElementById('chat-messages').appendChild(typing);
  scrollChat();

  try {
    const r = await fetch('/agents/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: msg})
    });
    const d = await r.json();
    typing.remove();
    if (d.message_type==='command_output'||d.message_type==='chain_output') addCommandOutput(d.content, d.metadata);
    else if (d.message_type==='warning'&&d.metadata?.requires_confirmation) addConfirmationPrompt(d.content, d.metadata.command);
    else addChatMsg(d.content, 'agent', d.sender);
    if (ws&&ws.readyState===1) ws.send(JSON.stringify({type:'set_state',state:'idle'}));
    loadSuggestions();
  } catch(e) {
    typing.remove();
    addChatMsg('Connection error. Core unreachable.','agent','SYSTEM');
    if (ws&&ws.readyState===1) ws.send(JSON.stringify({type:'set_state',state:'idle'}));
  }
}

function addChatMsg(text, type, sender) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg '+type;
  div.innerHTML = '<div class="msg-sender">'+(type==='user'?'YOU':(sender||'ELIOT').toUpperCase())+'</div>'+escapeHtml(text);
  box.appendChild(div); scrollChat();
}

function addCommandOutput(text, metadata) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg agent';
  const cmd = metadata?.command||'';
  const rc = metadata?.return_code;
  const analysis = metadata?.analysis;
  let h = '<div class="msg-sender">SHELL</div>';
  h += '<div style="color:var(--cyan);font-size:10px;margin-bottom:6px;">$ '+escapeHtml(cmd)+'</div>';
  if (rc!==undefined) h += '<div style="color:'+(rc===0?'var(--green)':'var(--red)')+';font-size:9px;margin-bottom:6px;">exit: '+rc+'</div>';
  if (analysis) {
    div.innerHTML = h+'<div style="background:rgba(0,255,65,0.05);border:1px solid rgba(0,255,65,0.2);padding:8px;margin-bottom:6px;font-size:11px;line-height:1.5;">'+escapeHtml(analysis)+'</div>'+'<details style="font-size:10px;color:#555;"><summary style="cursor:pointer;color:#666;">Raw output</summary><pre style="margin:6px 0 0 0;white-space:pre-wrap;font-size:10px;max-height:150px;overflow-y:auto;">'+escapeHtml(text)+'</pre></details>';
  } else {
    div.innerHTML = h+'<pre style="margin:0;white-space:pre-wrap;font-size:11px;">'+escapeHtml(text)+'</pre>';
  }
  box.appendChild(div); scrollChat();
}

function addConfirmationPrompt(text, command) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg agent'; div.style.borderColor = 'var(--orange)';
  div.innerHTML = '<div class="msg-sender" style="color:var(--orange);">WARNING</div><div style="color:var(--orange);margin-bottom:6px;">'+escapeHtml(text)+'</div><div style="display:flex;gap:6px;"><button onclick="document.getElementById(\'chat-input\').value=\'confirm '+escapeHtml(command)+'\';sendChat()" style="background:var(--red);color:#000;border:none;padding:4px 10px;cursor:pointer;font-weight:bold;font-size:10px;">Confirm</button><button onclick="document.getElementById(\'chat-input\').value=\'cancel\';sendChat()" style="background:#333;color:#fff;border:none;padding:4px 10px;cursor:pointer;font-size:10px;">Cancel</button></div>';
  box.appendChild(div); scrollChat();
}

function scrollChat() { const b=document.getElementById('chat-messages'); requestAnimationFrame(()=>b.scrollTop=b.scrollHeight); }
function escapeHtml(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>'); }
document.getElementById('chat-input').addEventListener('keydown', e => { if(e.key==='Enter')sendChat(); });

// ═══════════════════════════════════════════════════
// Prompt Suggestions
// ═══════════════════════════════════════════════════
async function loadSuggestions() {
  try {
    const r = await fetch('/tamagotchi/suggestions');
    const d = await r.json();
    const box = document.getElementById('chat-suggestions');
    box.innerHTML = (d.suggestions||[]).map(s =>
      '<div class="suggest-chip" onclick="document.getElementById(\'chat-input\').value=\''+escapeHtml(s.text).replace(/'/g,"\\'")+'\';sendChat()">'+escapeHtml(s.text)+'</div>'
    ).join('');
  } catch(e) {}
}

// ═══════════════════════════════════════════════════
// Network Topology (SVG)
// ═══════════════════════════════════════════════════
async function loadTopology() {
  try {
    const r = await fetch('/sentient/topology');
    const topo = await r.json();
    renderTopology(topo);
  } catch(e) {}
}

function renderTopology(topo) {
  const svg = document.getElementById('net-svg');
  if (!svg || !topo.nodes) return;
  const w = svg.parentElement.clientWidth || 600;
  const h = svg.parentElement.clientHeight || 400;
  let html = '';

  // Layout: force-directed simple
  const nodes = topo.nodes.map((n,i) => {
    const angle = (i / topo.nodes.length) * Math.PI * 2;
    const r = Math.min(w,h) * 0.35;
    return {...n, x: w/2 + Math.cos(angle)*r*(0.5+Math.random()*0.5), y: h/2 + Math.sin(angle)*r*(0.5+Math.random()*0.5)};
  });

  // Edges
  (topo.edges||[]).forEach(e => {
    const s = nodes.find(n=>n.id===e.source);
    const t = nodes.find(n=>n.id===e.target);
    if (s&&t) html += '<line class="net-edge active" x1="'+s.x+'" y1="'+s.y+'" x2="'+t.x+'" y2="'+t.y+'"/>';
  });

  // Nodes
  const colors = {self:'var(--green)',router:'var(--cyan)',server:'var(--orange)',workstation:'var(--text)',iot:'#888',wifi_ap:'#ff00ff',unknown:'#444'};
  const sevColors = {none:'var(--text)',low:'#888',medium:'var(--orange)',high:'var(--red)',critical:'#ff0040'};
  nodes.forEach(n => {
    const fill = n.type==='self'?'var(--green)':(sevColors[n.severity]||colors[n.type]||'#444');
    html += '<g class="net-node">';
    html += '<circle cx="'+n.x+'" cy="'+n.y+'" r="16" fill="'+fill+'" opacity="0.2" stroke="'+fill+'" stroke-width="1.5"/>';
    html += '<text x="'+n.x+'" y="'+(n.y+32)+'" text-anchor="middle" fill="'+fill+'">'+escapeHtml(n.label||n.ip)+'</text>';
    if (n.services) html += '<text x="'+n.x+'" y="'+(n.y+42)+'" text-anchor="middle" fill="#555" font-size="8">'+n.services+' svc</text>';
    html += '</g>';
  });

  svg.innerHTML = html;
}

// ═══════════════════════════════════════════════════
// Devices & WiFi
// ═══════════════════════════════════════════════════
async function loadDevices() {
  try {
    const r = await fetch('/sentient/devices');
    const d = await r.json();
    const box = document.getElementById('device-list');
    if (!d.devices||d.devices.length===0) { box.innerHTML='<span style="color:#555">No devices discovered yet</span>'; return; }
    box.innerHTML = d.devices.map(dev => {
      const sevColor = dev.vulnerabilities&&dev.vulnerabilities.length?'var(--red)':'var(--green)';
      return '<div class="metric-row"><span class="metric-label">'+escapeHtml(dev.ip)+(dev.hostname?' ('+escapeHtml(dev.hostname)+')':'')+'</span><span class="metric-value" style="color:'+sevColor+'">'+dev.device_type+' | '+dev.services.length+' svc</span></div>';
    }).join('');
  } catch(e) {}
}

async function loadWiFi() {
  try {
    const r = await fetch('/sentient/wifi');
    const d = await r.json();
    const box = document.getElementById('wifi-list');
    if (!d.access_points||d.access_points.length===0) { box.innerHTML='<span style="color:#555">No APs found</span>'; return; }
    box.innerHTML = d.access_points.map(ap =>
      '<div class="metric-row"><span class="metric-label">'+escapeHtml(ap.ssid||ap.bssid)+'</span><span class="metric-value">'+ap.signal+'dBm | Ch'+ap.channel+'</span></div>'
    ).join('');
  } catch(e) {}
}

async function triggerScan() {
  document.getElementById('scan-status').textContent='Scanning...';
  try {
    const r = await fetch('/sentient/scan',{method:'POST'});
    const d = await r.json();
    document.getElementById('scan-status').textContent='Found '+d.hosts_found+' hosts, '+d.wifi_aps+' APs in '+d.duration_seconds+'s';
    loadTopology(); loadDevices(); loadWiFi();
  } catch(e) { document.getElementById('scan-status').textContent='Scan failed'; }
}

// ═══════════════════════════════════════════════════
// Workflows
// ═══════════════════════════════════════════════════
async function loadWorkflows() {
  try {
    const r = await fetch('/agents/workflows/list');
    const d = await r.json();
    const box = document.getElementById('workflows-list');
    let html = '';
    for (const [name, wf] of Object.entries(d.workflows||{})) {
      html += '<div class="workflow-card" onclick="this.classList.toggle(\'expanded\')">';
      html += '<h4>'+name+'</h4><p>'+(wf.description||'')+'</p>';
      html += '<div class="wf-agents">'+(wf.agents||[]).map(a=>'<span class="wf-agent-tag">'+a+'</span>').join('')+'</div>';
      html += '<div class="wf-form">';
      html += '<label>Target IP / CIDR</label><input id="wf-target-'+name+'" placeholder="e.g. 192.168.1.1">';
      html += '<label>Custom prompt (optional)</label><input id="wf-prompt-'+name+'" placeholder="Override default prompt...">';
      html += '<button class="wf-run-btn" onclick="event.stopPropagation();runWFWithTarget(\''+name+'\')">Execute</button>';
      html += '</div></div>';
    }
    box.innerHTML = html || '<span style="color:#555">No workflows</span>';
  } catch(e) {}
}

async function runWFWithTarget(name) {
  const target = document.getElementById('wf-target-'+name)?.value||'';
  const prompt = document.getElementById('wf-prompt-'+name)?.value||'';
  const card = document.getElementById('wf-run-card');
  const output = document.getElementById('wf-output');
  card.style.display=''; output.innerHTML='<span style="color:var(--cyan)">Running '+name+'...</span>';
  if (ws&&ws.readyState===1) ws.send(JSON.stringify({type:'set_state',state:'thinking'}));
  try {
    const body = {message: prompt||('Execute workflow on target: '+target)};
    if (target) body.metadata = {target};
    const r = await fetch('/agents/workflow/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d = await r.json();
    output.innerHTML='<div style="color:var(--green);margin-bottom:6px;">Complete</div><pre style="margin:0;white-space:pre-wrap;font-size:11px;max-height:400px;overflow-y:auto;">'+escapeHtml(d.content)+'</pre>';
    if (ws&&ws.readyState===1) ws.send(JSON.stringify({type:'set_state',state:'idle'}));
  } catch(e) { output.innerHTML='<span style="color:var(--red)">Failed or timed out</span>'; if(ws&&ws.readyState===1)ws.send(JSON.stringify({type:'set_state',state:'idle'})); }
}

async function runPentest() {
  const target = document.getElementById('pentest-target').value.trim();
  if (!target) { document.getElementById('pentest-target').style.borderColor='var(--red)'; return; }
  document.getElementById('pentest-target').style.borderColor='var(--border)';
  const card = document.getElementById('wf-run-card');
  const output = document.getElementById('wf-output');
  card.style.display='';
  output.innerHTML='<div style="color:var(--red);margin-bottom:6px;">Pentesting '+escapeHtml(target)+'...</div><div style="color:#555;font-size:10px;">Recon → Scan → Web Scan → Analyze → Exploit → Report</div><div id="pentest-progress" style="margin-top:6px;"></div>';
  if (ws&&ws.readyState===1) { ws.send(JSON.stringify({type:'set_state',state:'thinking'})); ws.send(JSON.stringify({type:'set_text',text:'Pentesting '+target})); }
  try {
    const r = await fetch('/agents/pentest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target})});
    const d = await r.json();
    output.innerHTML='<div style="color:var(--green);margin-bottom:6px;font-family:Orbitron;font-size:10px;letter-spacing:2px;">PENTEST COMPLETE</div><div style="color:var(--cyan);font-size:9px;margin-bottom:10px;">Target: '+escapeHtml(target)+' | Steps: '+(d.metadata?.steps_completed||[]).join(', ')+'</div><pre style="margin:0;white-space:pre-wrap;font-size:11px;max-height:400px;overflow-y:auto;">'+escapeHtml(d.content)+'</pre>';
    if (ws&&ws.readyState===1) ws.send(JSON.stringify({type:'set_state',state:'idle'}));
  } catch(e) { output.innerHTML='<span style="color:var(--red)">Timed out or failed</span>'; if(ws&&ws.readyState===1)ws.send(JSON.stringify({type:'set_state',state:'idle'})); }
}

// ═══════════════════════════════════════════════════
// Tamagotchi Page
// ═══════════════════════════════════════════════════
async function loadTamagotchi() {
  try {
    const r = await fetch('/tamagotchi/notifications');
    const d = await r.json();
    const box = document.getElementById('notif-list');
    const pending = (d.notifications||[]).filter(n=>n.needs_auth&&n.auth_status==='pending');
    document.getElementById('notif-badge').style.display = pending.length>0?'inline':'none';
    document.getElementById('notif-badge').textContent = pending.length;

    if (!d.notifications||d.notifications.length===0) { box.innerHTML='<span style="color:#555">No notifications</span>'; return; }
    box.innerHTML = d.notifications.reverse().map(n => {
      const cls = n.auth_status||'info';
      let actions = '';
      if (n.needs_auth&&n.auth_status==='pending') {
        actions = '<div class="notif-actions"><button class="notif-btn approve" onclick="authNotif(\''+n.id+'\',true)">Approve</button><button class="notif-btn deny" onclick="authNotif(\''+n.id+'\',false)">Deny</button></div>';
      }
      return '<div class="notif-item '+cls+'"><div><div class="notif-title">'+escapeHtml(n.title)+'</div><div class="notif-meta">'+escapeHtml(n.message)+'</div></div>'+actions+'</div>';
    }).join('');
  } catch(e) {}

  try {
    const r = await fetch('/tamagotchi/exploits');
    const d = await r.json();
    const box = document.getElementById('exploit-queue');
    if (!d.exploits||d.exploits.length===0) { box.innerHTML='<span style="color:#555">No exploits queued</span>'; return; }
    box.innerHTML = d.exploits.map(e =>
      '<div class="metric-row"><span class="metric-label">'+escapeHtml(e.target)+' — '+escapeHtml(e.exploit_name||e.command?.substring(0,40))+'</span><span class="metric-value" style="color:'+(e.auth_status==='approved'?'var(--green)':'var(--orange)')+'">'+e.auth_status+'</span></div>'
    ).join('');
  } catch(e) {}

  try {
    const r = await fetch('/tamagotchi/knowledge');
    const d = await r.json();
    document.getElementById('knowledge-stats').innerHTML = Object.entries(d.stats||{}).map(([k,v])=>'<span class="metric-row"><span class="metric-label">'+k+'</span><span class="metric-value">'+v+'</span></span>').join('');
  } catch(e) {}
}

async function authNotif(id, approve) {
  const endpoint = approve ? '/tamagotchi/authorize' : '/tamagotchi/deny';
  await fetch(endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({notification_id:id})});
  loadTamagotchi();
}

// ═══════════════════════════════════════════════════
// Dashboard
// ═══════════════════════════════════════════════════
async function loadDashboard() {
  try {
    const r = await fetch('/system/info');
    const d = await r.json();
    const totalMem = (d.hardware.memory_gb||0).toFixed(1);
    const usedMem = ((d.hardware.memory_gb||0)-(d.metrics.memory_available_gb||0)).toFixed(1);
    document.getElementById('dash-hardware').innerHTML = '<div class="metric-row"><span class="metric-label">Target</span><span class="metric-value">'+d.hardware.target+'</span></div><div class="metric-row"><span class="metric-label">CPU</span><span class="metric-value">'+d.metrics.cpu_percent+'%</span></div><div class="metric-row"><span class="metric-label">Memory</span><span class="metric-value">'+d.metrics.memory_percent+'% ('+usedMem+'/'+totalMem+'GB)</span></div><div class="metric-row"><span class="metric-label">Disk</span><span class="metric-value">'+d.metrics.disk_percent+'%</span></div><div class="metric-row"><span class="metric-label">CUDA</span><span class="metric-value">'+(d.hardware.cuda_available?'Available':'N/A')+'</span></div>';
  } catch(e) {}
  try {
    const r = await fetch('/health/detailed');
    const d = await r.json();
    let svc = '';
    for (const [k,v] of Object.entries(d.services||{})) svc += '<div class="metric-row"><span class="metric-label">'+k+'</span><span class="metric-value" style="color:'+(v==='healthy'?'var(--green)':'var(--red)')+'">'+v+'</span></div>';
    document.getElementById('dash-services').innerHTML = svc||'<span style="color:#555">No data</span>';
  } catch(e) {}
  try {
    const r = await fetch('/agents/');
    const agents = await r.json();
    document.getElementById('dash-agents').innerHTML = agents.map(a=>'<div class="metric-row"><span class="metric-label">'+a.name+'</span><span class="metric-value">'+a.tasks_completed+' tasks | '+a.state+'</span></div>').join('');
  } catch(e) {}
}

// ═══════════════════════════════════════════════════
// Stealth Badge
// ═══════════════════════════════════════════════════
async function loadStealth() {
  try {
    const r = await fetch('/tamagotchi/status');
    const d = await r.json();
    // Update stealth badge from sentient or tamagotchi status
  } catch(e) {}
  try {
    const r2 = await fetch('/sentient/status');
    const d2 = await r2.json();
    const badge = document.getElementById('stealth-badge');
    badge.textContent = 'STEALTH ACTIVE';
    badge.className = 'stealth-badge';
  } catch(e) {}
}

// ═══════════════════════════════════════════════════
// Recent Activity Feed
// ═══════════════════════════════════════════════════
async function loadRecentActivity() {
  try {
    const r = await fetch('/sentient/events?since='+(Date.now()/1000-3600));
    const d = await r.json();
    const box = document.getElementById('recent-activity');
    if (!d.events||d.events.length===0) { box.innerHTML='<span style="color:#555">No recent activity</span>'; return; }
    box.innerHTML = d.events.slice(-15).reverse().map(e => {
      const t = new Date(e.timestamp*1000).toLocaleTimeString();
      return '<div style="padding:3px 0;border-bottom:1px solid #0d0d14;"><span style="color:#555">'+t+'</span> <span style="color:var(--cyan)">'+e.type+'</span></div>';
    }).join('');
  } catch(e) {}
}

// ═══════════════════════════════════════════════════
// Page Router
// ═══════════════════════════════════════════════════
function loadPageData(name) {
  if (name==='home') { loadRecentActivity(); }
  if (name==='network') { loadTopology(); loadDevices(); loadWiFi(); }
  if (name==='chat') { loadSuggestions(); }
  if (name==='workflows') { loadWorkflows(); }
  if (name==='tamagotchi') { loadTamagotchi(); }
  if (name==='system') { loadDashboard(); }
}

// ═══════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════
function initApp() {
  connectWS();
  initMatrix();
  updateRobot('idle','systems online');
  setTypingText('root@eliot:~# echo "Mr. Robot is watching..."');
  loadStealth();
  loadRecentActivity();
  loadSuggestions();
  setInterval(loadRecentActivity, 30000);
  setInterval(loadStealth, 60000);
  setInterval(()=>{try{fetch('/tamagotchi/notifications').then(r=>r.json()).then(d=>{const p=(d.notifications||[]).filter(n=>n.needs_auth&&n.auth_status==='pending');document.getElementById('notif-badge').style.display=p.length>0?'inline':'none';document.getElementById('notif-badge').textContent=p.length;});}catch(e){}}, 15000);
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def ui_home():
    return HTML_TEMPLATE
