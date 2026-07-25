"""
ELIOT Touch UI

Web-based touch interface served by the core service.
Pages: Home, Dashboard, Knowledge, Timeline, Chat, Reports
"""

import logging
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["ui"])

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>ELIOT</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Courier New', monospace;
    background: #0a0a0a;
    color: #00ff41;
    overflow: hidden;
    height: 100vh;
  }
  .header {
    background: #111;
    border-bottom: 1px solid #00ff41;
    padding: 8px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h1 { font-size: 18px; color: #00ff41; }
  .header .status { font-size: 12px; color: #666; }
  .nav {
    display: flex;
    gap: 4px;
    padding: 8px;
    background: #0d0d0d;
    border-bottom: 1px solid #1a1a1a;
    overflow-x: auto;
  }
  .nav button {
    background: #1a1a1a;
    color: #00ff41;
    border: 1px solid #333;
    padding: 6px 12px;
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
  }
  .nav button.active, .nav button:hover {
    background: #00ff41;
    color: #000;
  }
  .page { display: none; padding: 16px; height: calc(100vh - 90px); overflow-y: auto; }
  .page.active { display: block; }
  .card {
    background: #111;
    border: 1px solid #1a1a1a;
    padding: 12px;
    margin-bottom: 8px;
  }
  .card h3 { color: #00ff41; margin-bottom: 8px; font-size: 14px; }
  .metric { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #1a1a1a; }
  .metric .label { color: #666; }
  .metric .value { color: #00ff41; }
  .chat-box { display: flex; flex-direction: column; height: calc(100vh - 160px); }
  .chat-messages { flex: 1; overflow-y: auto; padding: 8px; }
  .chat-msg { margin-bottom: 8px; padding: 8px; background: #111; border-left: 2px solid #00ff41; }
  .chat-msg.user { border-left-color: #ff6600; }
  .chat-input { display: flex; gap: 8px; padding: 8px; }
  .chat-input input {
    flex: 1; background: #111; border: 1px solid #333; color: #00ff41;
    padding: 8px; font-family: inherit; font-size: 14px;
  }
  .chat-input button {
    background: #00ff41; color: #000; border: none;
    padding: 8px 16px; font-family: inherit; cursor: pointer;
  }
  .log-entry { font-size: 11px; padding: 4px 0; border-bottom: 1px solid #0d0d0d; color: #888; }
  .log-entry .time { color: #444; }
  .log-entry .action { color: #00ff41; }
</style>
</head>
<body>
<div class="header">
  <h1>ELIOT</h1>
  <div class="status" id="status">Connecting...</div>
</div>
<div class="nav">
  <button class="active" onclick="showPage('home')">Home</button>
  <button onclick="showPage('dashboard')">Dashboard</button>
  <button onclick="showPage('knowledge')">Knowledge</button>
  <button onclick="showPage('timeline')">Timeline</button>
  <button onclick="showPage('chat')">Chat</button>
  <button onclick="showPage('reports')">Reports</button>
</div>

<div id="page-home" class="page active">
  <div class="card"><h3>System Status</h3><div id="home-status">Loading...</div></div>
  <div class="card"><h3>Avatar</h3><div style="text-align:center;padding:20px;color:#333;">Avatar rendering (Godot WebSocket)</div></div>
</div>

<div id="page-dashboard" class="page">
  <div class="card"><h3>CPU / Memory / Disk</h3><div id="dash-metrics">Loading...</div></div>
  <div class="card"><h3>GPU</h3><div id="dash-gpu">Loading...</div></div>
  <div class="card"><h3>Services</h3><div id="dash-services">Loading...</div></div>
</div>

<div id="page-knowledge" class="page">
  <div class="card"><h3>Knowledge Base</h3><div id="kb-stats">Loading...</div></div>
  <div class="card"><h3>Search</h3>
    <input id="kb-search" style="width:100%;background:#111;border:1px solid #333;color:#00ff41;padding:8px;font-family:inherit;margin-bottom:8px;" placeholder="Search knowledge...">
    <div id="kb-results"></div>
  </div>
</div>

<div id="page-timeline" class="page">
  <div class="card"><h3>Recent Events</h3><div id="timeline-events">Loading...</div></div>
</div>

<div id="page-chat" class="page">
  <div class="chat-box">
    <div class="chat-messages" id="chat-messages"></div>
    <div class="chat-input">
      <input id="chat-input" placeholder="Type a message..." onkeydown="if(event.key==='Enter')sendChat()">
      <button onclick="sendChat()">Send</button>
    </div>
  </div>
</div>

<div id="page-reports" class="page">
  <div class="card"><h3>Generated Reports</h3><div id="reports-list">No reports yet.</div></div>
</div>

<script>
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  event.target.classList.add('active');
  loadPageData(name);
}

async function loadPageData(name) {
  if (name === 'dashboard') {
    try {
      const r = await fetch('/system/info');
      const d = await r.json();
      document.getElementById('dash-metrics').innerHTML =
        '<div class="metric"><span class="label">CPU</span><span class="value">' + d.metrics.cpu_percent + '%</span></div>' +
        '<div class="metric"><span class="label">Memory</span><span class="value">' + d.metrics.memory_percent + '%</span></div>' +
        '<div class="metric"><span class="label">Disk</span><span class="value">' + d.metrics.disk_percent + '%</span></div>';
      document.getElementById('dash-gpu').innerHTML =
        '<div class="metric"><span class="label">CUDA</span><span class="value">' + (d.hardware.cuda_available ? 'Yes' : 'No') + '</span></div>';
      document.getElementById('dash-services').innerHTML =
        '<div class="metric"><span class="label">Target</span><span class="value">' + d.hardware.target + '</span></div>';
    } catch(e) { document.getElementById('dash-metrics').innerHTML = 'Error loading metrics'; }
  }
  if (name === 'knowledge') {
    try {
      const r = await fetch('/knowledge/stats');
      const d = await r.json();
      document.getElementById('kb-stats').innerHTML =
        '<div class="metric"><span class="label">Documents</span><span class="value">' + d.total_documents + '</span></div>' +
        '<div class="metric"><span class="label">Embedding Dim</span><span class="value">' + d.embedding_dimensions + '</span></div>';
    } catch(e) {}
  }
  if (name === 'home') {
    try {
      const r = await fetch('/health/detailed');
      const d = await r.json();
      document.getElementById('home-status').innerHTML =
        '<div class="metric"><span class="label">Status</span><span class="value">' + d.status + '</span></div>' +
        '<div class="metric"><span class="label">Version</span><span class="value">' + d.version + '</span></div>' +
        '<div class="metric"><span class="label">Uptime</span><span class="value">' + Math.floor(d.uptime_seconds) + 's</span></div>';
      document.getElementById('status').textContent = 'v' + d.version + ' | ' + d.status;
    } catch(e) {}
  }
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  const box = document.getElementById('chat-messages');
  box.innerHTML += '<div class="chat-msg user">' + msg + '</div>';
  box.scrollTop = box.scrollHeight;
  try {
    const r = await fetch('/agents/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });
    const d = await r.json();
    box.innerHTML += '<div class="chat-msg">' + d.content.replace(/\\n/g, '<br>') + '</div>';
    box.scrollTop = box.scrollHeight;
  } catch(e) {
    box.innerHTML += '<div class="chat-msg">Error: could not reach ELIOT</div>';
  }
}

loadPageData('home');
setInterval(() => loadPageData('home'), 10000);
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def ui_home():
    return HTML_TEMPLATE
