"""
ELIOT Touch UI v4

Tamagotchi-centric cybersecurity dashboard with gamification,
interactive topology, logs, and documents.
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ELIOT</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
  --bg-root: #0a0e17;
  --bg-surface: #111827;
  --bg-elevated: #1a2332;
  --bg-hover: #1f2937;
  --border: #1f2937;
  --border-focus: #3b82f6;
  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  --accent: #3b82f6;
  --accent-dim: #2563eb;
  --accent-glow: rgba(59,130,246,0.15);
  --success: #10b981;
  --success-bg: rgba(16,185,129,0.1);
  --warning: #f59e0b;
  --warning-bg: rgba(245,158,11,0.1);
  --danger: #ef4444;
  --danger-bg: rgba(239,68,68,0.1);
  --info: #60a5fa;
  --info-bg: rgba(96,165,250,0.1);
  --critical: #ff4444;
  --high: #ff6b35;
  --medium: #f59e0b;
  --low: #60a5fa;
  --sidebar-w: 220px;
  --header-h: 52px;
  --xp-bar: #10b981;
}

* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; overflow:hidden; }
body { font-family:'Inter',-apple-system,sans-serif; background:var(--bg-root); color:var(--text-primary); }

/* Layout */
.app { display:flex; height:100vh; }
.sidebar { width:var(--sidebar-w); background:var(--bg-surface); border-right:1px solid var(--border); display:flex; flex-direction:column; flex-shrink:0; }
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
.header { height:var(--header-h); background:var(--bg-surface); border-bottom:1px solid var(--border); display:flex; align-items:center; padding:0 24px; justify-content:space-between; flex-shrink:0; }
.content { flex:1; overflow-y:auto; padding:24px; }

/* Sidebar */
.sidebar-logo { padding:16px 20px; border-bottom:1px solid var(--border); }
.sidebar-logo h1 { font-family:'JetBrains Mono',monospace; font-size:16px; font-weight:700; color:var(--accent); letter-spacing:2px; }
.sidebar-logo span { font-size:10px; color:var(--text-muted); display:block; margin-top:2px; letter-spacing:1px; }
.sidebar-nav { flex:1; padding:8px; overflow-y:auto; }
.nav-section { font-size:10px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:1.5px; padding:16px 12px 6px; }
.nav-item { display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:6px; cursor:pointer; color:var(--text-secondary); font-size:13px; font-weight:500; transition:all 0.15s; margin-bottom:2px; }
.nav-item:hover { background:var(--bg-hover); color:var(--text-primary); }
.nav-item.active { background:var(--accent-glow); color:var(--accent); font-weight:600; }
.nav-item svg { width:18px; height:18px; flex-shrink:0; }
.nav-badge { margin-left:auto; background:var(--danger); color:#fff; font-size:10px; font-weight:700; padding:2px 6px; border-radius:10px; min-width:18px; text-align:center; }
.sidebar-footer { padding:12px 16px; border-top:1px solid var(--border); }
.status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:6px; }
.status-dot.on { background:var(--success); box-shadow:0 0 6px var(--success); }
.status-dot.off { background:var(--danger); }
.sidebar-footer .status-text { font-size:11px; color:var(--text-muted); }

/* Header */
.header-title { font-size:15px; font-weight:600; }
.header-title .breadcrumb { color:var(--text-muted); font-weight:400; margin-left:6px; }
.header-actions { display:flex; gap:8px; align-items:center; }

/* Buttons */
.btn { padding:7px 14px; border-radius:6px; border:1px solid var(--border); background:var(--bg-elevated); color:var(--text-primary); font-size:12px; font-weight:500; cursor:pointer; transition:all 0.15s; font-family:inherit; }
.btn:hover { background:var(--bg-hover); border-color:var(--text-muted); }
.btn-primary { background:var(--accent); border-color:var(--accent); color:#fff; }
.btn-primary:hover { background:var(--accent-dim); }
.btn-danger { background:var(--danger); border-color:var(--danger); color:#fff; }
.btn-sm { padding:4px 10px; font-size:11px; }

/* Cards */
.card { background:var(--bg-surface); border:1px solid var(--border); border-radius:8px; }
.card-header { padding:14px 18px; border-bottom:1px solid var(--border); font-size:13px; font-weight:600; display:flex; align-items:center; justify-content:space-between; }
.card-body { padding:18px; }

/* Stats Grid */
.stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:24px; }
.stat-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:8px; padding:18px; }
.stat-label { font-size:11px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }
.stat-value { font-size:28px; font-weight:700; font-family:'JetBrains Mono',monospace; }
.stat-value.critical { color:var(--critical); }
.stat-value.high { color:var(--high); }
.stat-value.medium { color:var(--medium); }
.stat-value.low { color:var(--low); }
.stat-value.accent { color:var(--accent); }
.stat-value.success { color:var(--success); }
.stat-sub { font-size:11px; color:var(--text-muted); margin-top:4px; }

/* Table */
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; padding:10px 14px; font-size:11px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid var(--border); white-space:nowrap; }
td { padding:10px 14px; border-bottom:1px solid var(--border); color:var(--text-secondary); }
tr:hover td { background:var(--bg-hover); }

/* Severity Badges */
.sev { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }
.sev-critical { background:rgba(255,68,68,0.15); color:#ff6b6b; }
.sev-high { background:rgba(255,107,53,0.15); color:#ff8c60; }
.sev-medium { background:rgba(245,158,11,0.15); color:#fbbf24; }
.sev-low { background:rgba(96,165,250,0.15); color:#93bbfd; }
.sev-info { background:rgba(107,114,128,0.15); color:#9ca3af; }
.sev-none { background:rgba(107,114,128,0.15); color:#9ca3af; }

/* Status Badges */
.status { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500; }
.status-open { background:var(--danger-bg); color:var(--danger); }
.status-progress { background:var(--warning-bg); color:var(--warning); }
.status-fixed { background:var(--success-bg); color:var(--success); }
.status-accepted { background:var(--info-bg); color:var(--info); }

/* Activity Feed */
.feed-item { display:flex; gap:12px; padding:12px 0; border-bottom:1px solid var(--border); }
.feed-item:last-child { border-bottom:none; }
.feed-icon { width:32px; height:32px; border-radius:6px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:14px; }
.feed-icon.scan { background:var(--accent-glow); color:var(--accent); }
.feed-icon.vuln { background:var(--danger-bg); color:var(--danger); }
.feed-icon.device { background:var(--success-bg); color:var(--success); }
.feed-icon.info { background:rgba(107,114,128,0.15); color:var(--text-muted); }
.feed-text { font-size:13px; color:var(--text-secondary); }
.feed-text strong { color:var(--text-primary); font-weight:600; }
.feed-time { font-size:11px; color:var(--text-muted); margin-top:2px; }

/* Tabs */
.tabs { display:flex; gap:0; border-bottom:1px solid var(--border); margin-bottom:20px; }
.tab { padding:10px 16px; font-size:13px; font-weight:500; color:var(--text-muted); cursor:pointer; border-bottom:2px solid transparent; transition:all 0.15s; }
.tab:hover { color:var(--text-secondary); }
.tab.active { color:var(--accent); border-bottom-color:var(--accent); }

/* Form */
.form-group { margin-bottom:16px; }
.form-label { display:block; font-size:12px; font-weight:500; color:var(--text-secondary); margin-bottom:6px; }
.form-input { width:100%; padding:8px 12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:6px; color:var(--text-primary); font-family:'JetBrains Mono',monospace; font-size:13px; outline:none; transition:border-color 0.15s; }
.form-input:focus { border-color:var(--accent); }
.form-input::placeholder { color:var(--text-muted); }
select.form-input { appearance:none; background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 10px center; padding-right:32px; }

/* Terminal Output */
.terminal { background:#000; border:1px solid var(--border); border-radius:6px; padding:14px; font-family:'JetBrains Mono',monospace; font-size:12px; line-height:1.6; color:#00ff41; max-height:400px; overflow-y:auto; white-space:pre-wrap; word-break:break-all; }
.terminal .cmd { color:var(--accent); }
.terminal .err { color:var(--danger); }
.terminal .warn { color:var(--warning); }

/* Chat */
.chat-container { display:flex; flex-direction:column; height:calc(100vh - var(--header-h) - 48px); }
.chat-messages { flex:1; overflow-y:auto; padding-bottom:16px; }
.chat-msg { margin-bottom:16px; max-width:85%; }
.chat-msg.user { margin-left:auto; }
.chat-msg .bubble { padding:10px 14px; border-radius:10px; font-size:13px; line-height:1.5; }
.chat-msg.user .bubble { background:var(--accent); color:#fff; border-bottom-right-radius:2px; }
.chat-msg.assistant .bubble { background:var(--bg-elevated); color:var(--text-secondary); border-bottom-left-radius:2px; border:1px solid var(--border); }
.chat-msg .meta { font-size:10px; color:var(--text-muted); margin-top:4px; padding:0 4px; }
.chat-input-wrap { display:flex; gap:8px; padding-top:12px; border-top:1px solid var(--border); }
.chat-input { flex:1; padding:10px 14px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:8px; color:var(--text-primary); font-family:inherit; font-size:13px; outline:none; resize:none; min-height:42px; max-height:120px; }
.chat-input:focus { border-color:var(--accent); }

/* Suggestions */
.suggestions { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
.suggestion { padding:6px 12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:16px; font-size:12px; color:var(--text-secondary); cursor:pointer; transition:all 0.15s; }
.suggestion:hover { border-color:var(--accent); color:var(--accent); background:var(--accent-glow); }

/* Topology SVG */
.topo-container { width:100%; height:500px; background:var(--bg-root); border:1px solid var(--border); border-radius:8px; overflow:hidden; position:relative; }
.topo-container svg { width:100%; height:100%; }
.topo-node { cursor:pointer; }
.topo-node:hover circle { stroke:var(--accent); stroke-width:2; }
.topo-label { font-family:'JetBrains Mono',monospace; font-size:10px; fill:var(--text-secondary); text-anchor:middle; }
.topo-edge { stroke:var(--border); stroke-width:1; }

/* Topology Detail Panel */
.topo-detail { position:absolute; right:0; top:0; width:320px; height:100%; background:var(--bg-surface); border-left:1px solid var(--border); padding:16px; overflow-y:auto; transform:translateX(100%); transition:transform 0.2s ease; z-index:10; }
.topo-detail.open { transform:translateX(0); }
.topo-detail-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.topo-detail-close { cursor:pointer; color:var(--text-muted); font-size:18px; }
.topo-detail-close:hover { color:var(--text-primary); }

/* Gamification */
.xp-bar-container { height:20px; background:var(--bg-elevated); border-radius:10px; overflow:hidden; margin:8px 0; border:1px solid var(--border); }
.xp-bar-fill { height:100%; background:linear-gradient(90deg, var(--xp-bar), var(--success)); border-radius:10px; transition:width 0.5s ease; }
.xp-bar-text { position:relative; top:-18px; text-align:center; font-size:10px; font-weight:600; color:var(--text-primary); }

.achievement-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); gap:12px; }
.achievement-card { background:var(--bg-elevated); border:1px solid var(--border); border-radius:8px; padding:12px; text-align:center; }
.achievement-card.unlocked { border-color:var(--accent); background:var(--accent-glow); }
.achievement-icon { font-size:24px; margin-bottom:6px; }
.achievement-name { font-size:11px; font-weight:600; color:var(--text-primary); }
.achievement-desc { font-size:10px; color:var(--text-muted); margin-top:2px; }
.achievement-locked .achievement-icon { opacity:0.3; }
.achievement-locked .achievement-name { color:var(--text-muted); }

/* Tamagotchi Avatar */
.avatar-container { display:flex; flex-direction:column; align-items:center; padding:20px; position:relative; }
.avatar-ascii { font-family:'JetBrains Mono',monospace; font-size:12px; line-height:1.2; color:var(--accent); white-space:pre; text-align:center; position:relative; transition:all 0.3s ease; }
.avatar-state { margin-top:12px; font-size:14px; font-weight:600; color:var(--accent); text-transform:capitalize; }

/* Avatar state animations */
@keyframes avatar-idle-glow { 0%,100%{box-shadow:0 0 8px rgba(100,100,120,0.15)} 50%{box-shadow:0 0 16px rgba(100,100,120,0.25)} }
@keyframes avatar-scan-sweep { 0%{background-position:0% 0%} 100%{background-position:0% 100%} }
@keyframes avatar-scan-eyes { 0%,40%{opacity:1} 45%{opacity:0.3} 50%{opacity:1} 90%{opacity:1} 95%{opacity:0.3} 100%{opacity:1} }
@keyframes avatar-analyze-spin { 0%{text-shadow:0 0 4px var(--success)} 50%{text-shadow:0 0 12px var(--success)} 100%{text-shadow:0 0 4px var(--success)} }
@keyframes avatar-exploit-flash { 0%,100%{opacity:1;text-shadow:0 0 4px var(--danger)} 50%{opacity:0.7;text-shadow:0 0 20px var(--danger)} }
@keyframes avatar-crack-churn { 0%{letter-spacing:0} 50%{letter-spacing:1px} 100%{letter-spacing:0} }
@keyframes avatar-alert-shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-3px)} 75%{transform:translateX(3px)} }
@keyframes avatar-alert-flash { 0%,100%{opacity:1} 50%{opacity:0.4} }
@keyframes avatar-sleep-breathe { 0%,100%{opacity:0.6;transform:scale(1)} 50%{opacity:0.85;transform:scale(1.01)} }
@keyframes avatar-map-pulse { 0%,100%{text-shadow:0 0 3px var(--info)} 50%{text-shadow:0 0 14px var(--info)} }
@keyframes avatar-report-type { 0%{opacity:0.7} 50%{opacity:1} 100%{opacity:0.7} }
@keyframes avatar-thinking-dots { 0%{opacity:1} 50%{opacity:0.3} 100%{opacity:1} }
@keyframes avatar-border-glow { 0%,100%{box-shadow:inset 0 0 8px rgba(0,100,255,0.05)} 50%{box-shadow:inset 0 0 16px rgba(0,100,255,0.12)} }
@keyframes avatar-exploit-border { 0%,100%{box-shadow:inset 0 0 8px rgba(255,50,50,0.08)} 50%{box-shadow:inset 0 0 20px rgba(255,50,50,0.2)} }
@keyframes avatar-success-border { 0%,100%{box-shadow:inset 0 0 8px rgba(0,200,100,0.05)} 50%{box-shadow:inset 0 0 16px rgba(0,200,100,0.12)} }

.avatar-anim-idle { animation: avatar-idle-glow 4s ease-in-out infinite; border-radius:8px; }
.avatar-anim-scanning .avatar-ascii { animation: avatar-scan-eyes 3s ease-in-out infinite; }
.avatar-anim-scanning { animation: avatar-border-glow 2s ease-in-out infinite; border-radius:8px; }
.avatar-anim-analyzing .avatar-ascii { animation: avatar-analyze-spin 2s ease-in-out infinite; }
.avatar-anim-exploiting .avatar-ascii { animation: avatar-exploit-flash 0.6s ease-in-out infinite; }
.avatar-anim-exploiting { animation: avatar-exploit-border 1s ease-in-out infinite; border-radius:8px; }
.avatar-anim-cracking .avatar-ascii { animation: avatar-crack-churn 1.5s ease-in-out infinite; }
.avatar-anim-alert .avatar-ascii { animation: avatar-alert-shake 0.3s ease-in-out infinite, avatar-alert-flash 0.8s ease-in-out infinite; }
.avatar-anim-sleeping .avatar-ascii { animation: avatar-sleep-breathe 4s ease-in-out infinite; }
.avatar-anim-mapping .avatar-ascii { animation: avatar-map-pulse 2.5s ease-in-out infinite; }
.avatar-anim-reporting .avatar-ascii { animation: avatar-report-type 3s ease-in-out infinite; }

/* Logs */
.log-entry { font-family:'JetBrains Mono',monospace; font-size:12px; padding:8px 12px; border-bottom:1px solid var(--border); display:flex; gap:12px; }
.log-time { color:var(--text-muted); min-width:80px; }
.log-type { min-width:80px; font-weight:600; }
.log-type.xp { color:var(--success); }
.log-type.achievement { color:var(--accent); }
.log-type.penalty { color:var(--danger); }
.log-type.level_up { color:var(--warning); }
.log-type.info { color:var(--text-muted); }
.log-message { color:var(--text-secondary); flex:1; }

/* Streak */
.streak-container { display:flex; gap:12px; margin:12px 0; }
.streak-item { background:var(--bg-elevated); border:1px solid var(--border); border-radius:8px; padding:8px 12px; text-align:center; flex:1; }
.streak-value { font-size:18px; font-weight:700; font-family:'JetBrains Mono',monospace; color:var(--accent); }
.streak-label { font-size:10px; color:var(--text-muted); margin-top:2px; }

/* Scrollbar */
::-webkit-scrollbar { width:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:var(--text-muted); }

/* Animations */
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.pulse { animation:pulse 2s infinite; }
@keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.fade-in { animation:fadeIn 0.2s ease-out; }
@keyframes glow { 0%,100%{box-shadow:0 0 5px var(--accent)} 50%{box-shadow:0 0 20px var(--accent)} }
.glow { animation:glow 2s infinite; }
</style>
</head>
<body>
<div class="app">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-logo">
      <h1>ELIOT</h1>
      <span>INTELLIGENCE TERMINAL</span>
    </div>
    <nav class="sidebar-nav">
      <div class="nav-section">Operations</div>
      <div class="nav-item active" data-page="overview" onclick="showPage('overview')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        Overview
      </div>
      <div class="nav-item" data-page="map" onclick="showPage('map')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        Map
        <span class="nav-badge" id="nav-devices" style="display:none">0</span>
      </div>
      <div class="nav-item" data-page="scan" onclick="showPage('scan')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
        Scan
      </div>
      <div class="nav-item" data-page="findings" onclick="showPage('findings')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Findings
        <span class="nav-badge" id="nav-vulns" style="display:none">0</span>
      </div>

      <div class="nav-section">Agent</div>
      <div class="nav-item" data-page="tamagotchi" onclick="showPage('tamagotchi')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Tamagotchi
        <span class="nav-badge" id="nav-notifs" style="display:none">0</span>
      </div>
      <div class="nav-item" data-page="intel" onclick="showPage('intel')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        Intel
      </div>

      <div class="nav-section">Knowledge</div>
      <div class="nav-item" data-page="knowledge" onclick="showPage('knowledge')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        Knowledge
      </div>

      <div class="nav-section">System</div>
      <div class="nav-item" data-page="logs" onclick="showPage('logs')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        Logs
      </div>
      <div class="nav-item" data-page="documents" onclick="showPage('documents')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        Documents
      </div>
      <div class="nav-item" data-page="settings" onclick="showPage('settings')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        Settings
      </div>
    </nav>
    <div class="sidebar-footer">
      <span class="status-dot on" id="status-dot"></span>
      <span class="status-text" id="status-text">Systems online</span>
    </div>
  </div>

  <!-- Main Content -->
  <div class="main">
    <div class="header">
      <div class="header-title" id="page-title">Overview</div>
      <div class="header-actions">
        <span id="clock" style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-muted)"></span>
        <button class="btn btn-sm" onclick="refreshCurrentPage()">↻ Refresh</button>
      </div>
    </div>
    <div class="content" id="content"></div>
  </div>
</div>

<script>
const API = '';
let currentPage = 'overview';
let chatMessages = [];
let ws = null;
let selectedDevice = null;

// Clock
function updateClock() {
  const d = new Date();
  document.getElementById('clock').textContent = d.toLocaleTimeString('en-US',{hour12:false}) + ' ' + d.toLocaleDateString('en-US',{month:'short',day:'numeric'});
}
setInterval(updateClock, 1000);
updateClock();

// Page Router
function showPage(page) {
  currentPage = page;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  const titles = {
    overview: 'Overview', map: 'Network Map', scan: 'Scan & Attack',
    findings: 'Findings', tamagotchi: 'Tamagotchi Agent', intel: 'Intel',
    knowledge: 'Knowledge Base', logs: 'System Logs', documents: 'Documents',
    settings: 'Settings'
  };
  document.getElementById('page-title').innerHTML = titles[page] || page;
  const renderers = {
    overview: renderOverview, map: renderMap, scan: renderScan,
    findings: renderFindings, tamagotchi: renderTamagotchi,
    intel: renderIntel, knowledge: renderKnowledge,
    logs: renderLogs, documents: renderDocuments,
    settings: renderSettings
  };
  (renderers[page] || renderOverview)();
}

function refreshCurrentPage() { showPage(currentPage); }

// Overview Page
async function renderOverview() {
  const c = document.getElementById('content');
  c.innerHTML = '<div class="fade-in"><div class="stats-grid" id="stats-grid"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:16px" id="overview-cols"></div></div>';

  const [status, devices, tamagotchi, wifi, topology] = await Promise.all([
    fetch(API+'/sentient/status').then(r=>r.json()).catch(()=>({devices:0,wifi_aps:0,running:false})),
    fetch(API+'/sentient/devices').then(r=>r.json()).catch(()=>({devices:[]})),
    fetch(API+'/tamagotchi/status').then(r=>r.json()).catch(()=>({})),
    fetch(API+'/sentient/wifi').then(r=>r.json()).catch(()=>({access_points:[]})),
    fetch(API+'/sentient/topology').then(r=>r.json()).catch(()=>({nodes:[],edges:[]}))
  ]);

  const devs = devices.devices || [];
  const vulns = [];
  devs.forEach(d => { (d.vulns||[]).forEach(v => vulns.push({...v, device:d.ip})); });

  const sg = document.getElementById('stats-grid');
  sg.innerHTML = `
    <div class="stat-card"><div class="stat-label">Devices</div><div class="stat-value accent">${devs.length}</div><div class="stat-sub">on local network</div></div>
    <div class="stat-card"><div class="stat-label">WiFi Networks</div><div class="stat-value success">${(wifi.access_points||[]).length}</div><div class="stat-sub">detected nearby</div></div>
    <div class="stat-card"><div class="stat-label">Findings</div><div class="stat-value ${vulns.length?'medium':'success'}">${vulns.length}</div><div class="stat-sub">vulnerabilities found</div></div>
    <div class="stat-card"><div class="stat-label">Scan Status</div><div class="stat-value" style="font-size:18px;color:${status.running?'var(--success)':'var(--text-muted)'}">${status.running?'Active':'Idle'}</div><div class="stat-sub">sentient engine</div></div>
    <div class="stat-card"><div class="stat-label">Agent State</div><div class="stat-value" style="font-size:18px;color:var(--accent)">${tamagotchi.state||'idle'}</div><div class="stat-sub">tamagotchi</div></div>
    <div class="stat-card"><div class="stat-label">Knowledge</div><div class="stat-value info">${(tamagotchi.knowledge_stats||{}).total||0}</div><div class="stat-sub">entries indexed</div></div>
  `;

  const cols = document.getElementById('overview-cols');
  let devRows = devs.map(d => `<tr><td><code style="color:var(--accent)">${d.ip}</code></td><td>${d.hostname||'-'}</td><td>${d.os_guess||'-'}</td><td><span class="sev sev-${d.type==='router'?'high':d.type==='server'?'medium':'info'}">${d.type||'unknown'}</span></td></tr>`).join('');
  if(!devRows) devRows = '<tr><td colspan="4" style="color:var(--text-muted);text-align:center;padding:30px">No devices discovered yet. Click Scan to start.</td></tr>';

  let apRows = (wifi.access_points||[]).slice(0,10).map(a => `<tr><td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${a.ssid}</td><td style="font-family:'JetBrains Mono',monospace;font-size:11px">${a.bssid}</td><td>${a.channel}</td><td style="color:${a.signal>-60?'var(--success)':a.signal>-75?'var(--warning)':'var(--danger)'}">${a.signal} dBm</td><td>${a.encryption==='on'?'<span style="color:var(--success)">WPA2</span>':'<span style="color:var(--danger)">Open</span>'}</td></tr>`).join('');

  cols.innerHTML = `
    <div class="card">
      <div class="card-header">Discovered Devices <button class="btn btn-sm" onclick="showPage('map')">View Map →</button></div>
      <div class="card-body table-wrap"><table><thead><tr><th>IP</th><th>Hostname</th><th>OS</th><th>Type</th></tr></thead><tbody>${devRows}</tbody></table></div>
    </div>
    <div class="card">
      <div class="card-header">WiFi Networks <span style="font-size:11px;color:var(--text-muted)">(top 10)</span></div>
      <div class="card-body table-wrap"><table><thead><tr><th>SSID</th><th>BSSID</th><th>CH</th><th>Signal</th><th>Enc</th></tr></thead><tbody>${apRows||'<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:30px">No WiFi data yet</td></tr>'}</tbody></table></div>
    </div>
  `;

  updateBadges(devs.length, vulns.length);
}

// Map Page with Interactive Topology + Detail Panel
async function renderMap() {
  const {topology, devices, wifi, tamaStatus} = mapData || await fetchMapData();

  const devs = devices.devices || [];
  const nodeCount = (topology.nodes||[]).length;
  const edgeCount = (topology.edges||[]).length;
  const phase = tamaStatus.current_phase || 'idle';
  const thought = tamaStatus.current_thought || '...';
  const isScanning = tamaStatus.state === 'scanning';
  const stateColors2 = {idle:'var(--text-muted)',scanning:'var(--accent)',mapping:'var(--info)',cracking:'var(--warning)',analyzing:'var(--success)',exploiting:'var(--danger)',alert:'var(--danger)',sleeping:'var(--text-muted)'};

  const c = document.getElementById('content');
  c.innerHTML = `<div class="fade-in">
    <div id="map-status-bar" style="display:flex;align-items:center;gap:12px;margin-bottom:12px;padding:10px 16px;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px">
      <div style="width:8px;height:8px;border-radius:50%;background:${isScanning?'var(--accent)':'var(--text-muted)'};${isScanning?'animation:pulse 1.5s infinite':''}"></div>
      <span style="font-size:12px;font-weight:600;color:${stateColors2[tamaStatus.state]||'var(--text-muted)'}">${tamaStatus.state||'unknown'}</span>
      <span style="font-size:11px;color:var(--text-muted)">|</span>
      <span style="font-size:11px;color:var(--text-secondary)">${nodeCount} nodes · ${edgeCount} edges · ${devs.length} devices · ${(wifi.access_points||[]).length} APs</span>
      <span style="font-size:11px;color:var(--text-muted)">|</span>
      <span style="font-size:11px;color:var(--text-secondary)">${phase.replace(/_/g,' ')}</span>
      <span style="flex:1"></span>
      <span id="map-freeze-badge" style="display:none;align-items:center;gap:6px;padding:3px 10px;background:rgba(255,180,50,0.15);border:1px solid rgba(255,180,50,0.3);border-radius:6px;font-size:10px;color:#ffb432;cursor:pointer" onclick="unfreezeMap()">
        <span style="font-size:10px">⏸</span> Paused <span style="font-size:9px;opacity:0.7">[click to resume]</span>
      </span>
      <span style="font-size:10px;color:var(--text-muted);font-family:'JetBrains Mono',monospace;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${thought}</span>
    </div>
    <div style="position:relative">
      <div class="topo-container" id="topo"></div>
      <div class="topo-detail" id="topo-detail">
        <div class="topo-detail-header">
          <h3 style="font-size:14px;font-weight:600">Device Details</h3>
          <span class="topo-detail-close" onclick="closeDeviceDetail()">×</span>
        </div>
        <div id="device-detail-content"></div>
      </div>
    </div>
    <div style="margin-top:16px" id="map-table"></div>
  </div>`;

  renderTopologySVG(topology, devices);

  // Interaction listeners: freeze auto-refresh when user interacts with the map
  const topoEl = document.getElementById('topo');
  if(topoEl) {
    ['mousedown','click','wheel'].forEach(evt => topoEl.addEventListener(evt, freezeMap));
    topoEl.addEventListener('mouseenter', freezeMap);
    topoEl.addEventListener('touchstart', freezeMap, {passive:true});
  }

  let rows = devs.map(d => `<tr onclick="showDeviceDetail('${d.ip}')" style="cursor:pointer"><td><code style="color:var(--accent)">${d.ip}</code></td><td>${d.hostname||'-'}</td><td>${d.mac||'-'}</td><td>${d.os_guess||'-'}</td><td><span class="sev sev-${d.type==='router'?'high':'info'}">${d.type||'?'}</span></td><td>${(d.services||[]).length}</td></tr>`).join('');
  if(!rows) rows = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:24px">No devices discovered</td></tr>';

  document.getElementById('map-table').innerHTML = `
    <div class="card">
      <div class="card-header">Device Inventory <span style="color:var(--text-muted);font-weight:400;font-size:12px">${devs.length} hosts</span></div>
      <div class="card-body table-wrap"><table><thead><tr><th>IP</th><th>Hostname</th><th>MAC</th><th>OS</th><th>Type</th><th>Services</th></tr></thead><tbody>${rows}</tbody></table></div>
    </div>`;
}

function renderTopologySVG(topo, devices) {
  const el = document.getElementById('topo');
  if(!topo.nodes||!topo.nodes.length) {
    el.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:13px"><div style="font-size:48px;margin-bottom:16px;opacity:0.3">🌐</div><div>No topology data yet</div><div style="font-size:11px;margin-top:4px">Run a scan to discover the network</div></div>';
    return;
  }
  const W = el.clientWidth || 900, H = el.clientHeight || 500;
  const cx = W/2, cy = H/2;
  const positions = {};

  // Find self node (center of map)
  const selfNode = topo.nodes.find(n => n.type === 'self');
  const routerNode = topo.nodes.find(n => n.type === 'router');
  const wifiNodes = topo.nodes.filter(n => n.type === 'wifi_ap');
  const deviceNodes = topo.nodes.filter(n => n.type !== 'self' && n.type !== 'router' && n.type !== 'wifi_ap');

  // Position: self at center, router close, devices in rings by signal/proximity, WiFi APs on outer ring
  if(selfNode) positions[selfNode.id] = { x: cx, y: cy };
  if(routerNode) positions[routerNode.id] = { x: cx + 80, y: cy };

  // Group devices by subnet
  const subnets = {};
  deviceNodes.forEach(d => {
    const ip = d.ip || '';
    const subnet = ip.split('.').slice(0,3).join('.');
    if(!subnets[subnet]) subnets[subnet] = [];
    subnets[subnet].push(d);
  });

  // Position devices in concentric rings by subnet
  let devRing = 0;
  for(const [subnet, devs] of Object.entries(subnets)) {
    const baseR = 140 + devRing * 90;
    devs.forEach((d, i) => {
      const angle = (2*Math.PI*i/devs.length) - Math.PI/2 + devRing * 0.3;
      const signal = d.signal || 0;
      // Closer = stronger signal (for WiFi), or just evenly spaced
      const r = signal < -70 ? baseR + 30 : signal < -50 ? baseR : baseR - 20;
      positions[d.id] = { x: cx + r*Math.cos(angle), y: cy + r*Math.sin(angle) };
    });
    devRing++;
  }

  // Position WiFi APs on outer ring with signal-based distance
  const apBaseR = Math.min(W, H) * 0.42;
  wifiNodes.forEach((ap, i) => {
    const angle = (2*Math.PI*i/wifiNodes.length) - Math.PI/2;
    const signal = ap.signal || -80;
    // Strong signal = closer to center
    const signalNorm = Math.max(0, Math.min(1, (signal + 90) / 60)); // -90dBm=0, -30dBm=1
    const r = apBaseR - signalNorm * 60;
    positions[ap.id] = { x: cx + r*Math.cos(angle), y: cy + r*Math.sin(angle) };
  });

  let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
  svg += `<defs>`;
  svg += `<filter id="glow"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`;
  svg += `<filter id="shadow"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.3"/></filter>`;
  svg += `<radialGradient id="rangeGrad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#3b82f6" stop-opacity="0.03"/><stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/></radialGradient>`;
  svg += `</defs>`;

  // Distance rings (Masego-style scale)
  [60, 140, 230, 320].forEach((r, i) => {
    svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#1f2937" stroke-width="0.5" stroke-dasharray="4,4" opacity="0.5"/>`;
    svg += `<text x="${cx+r+4}" y="${cy-4}" font-size="8" fill="#4b5563" font-family="JetBrains Mono,monospace">${r < 100 ? '' : ''}${['LAN','WiFi','Extended','WAN'][i]}</text>`;
  });

  // Range fill
  svg += `<circle cx="${cx}" cy="${cy}" r="320" fill="url(#rangeGrad)"/>`;

  // Edges (fix: backend uses source/target, not from/to)
  (topo.edges||[]).forEach(e => {
    const fromId = e.source || e.from;
    const toId = e.target || e.to;
    const a = positions[fromId], b = positions[toId];
    if(!a||!b) return;
    const typeColors = {route:'#f59e0b', lan:'#3b82f6', wifi:'#10b981'};
    const color = typeColors[e.type] || '#1f2937';
    svg += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${color}" stroke-width="1" opacity="0.4"/>`;
    // Connection label
    const mx = (a.x+b.x)/2, my = (a.y+b.y)/2;
    if(e.label) svg += `<text x="${mx}" y="${my-6}" font-size="7" fill="#6b7280" text-anchor="middle" font-family="JetBrains Mono,monospace">${e.label}</text>`;
  });

  // Nodes
  const nodeColors = {self:'#3b82f6',router:'#f59e0b',wifi_ap:'#10b981',workstation:'#60a5fa',server:'#ff6b35',mobile:'#a78bfa',iot:'#6ee7b7',printer:'#fbbf24',nas:'#f472b6',unknown:'#6b7280'};
  const nodeIcons = {self:'🛡',router:'📡',wifi_ap:'📶',workstation:'💻',server:'🖥',mobile:'📱',iot:'🏠',printer:'🖨',nas:'💾',unknown:'❓'};
  const nodeRadii = {self:22,router:18,wifi_ap:14,workstation:12,server:12,mobile:10,iot:10,printer:10,nas:10,unknown:10};

  topo.nodes.forEach(n => {
    const p = positions[n.id];
    if(!p) return;
    const color = nodeColors[n.type] || '#6b7280';
    const icon = nodeIcons[n.type] || '❓';
    const r = nodeRadii[n.type] || 10;

    svg += `<g class="topo-node" transform="translate(${p.x},${p.y})" onclick="showDeviceDetail('${n.ip||n.id}')" style="cursor:pointer">`;
    // Outer glow
    if(n.type === 'self' || n.type === 'router') {
      svg += `<circle r="${r+6}" fill="${color}" opacity="0.08" filter="url(#glow)"/>`;
    }
    // Signal ring for WiFi APs
    if(n.type === 'wifi_ap' && n.signal) {
      const sigNorm = Math.max(0.1, Math.min(0.8, (n.signal + 90) / 60));
      svg += `<circle r="${r+4}" fill="none" stroke="${color}" stroke-width="1" opacity="${sigNorm}" stroke-dasharray="2,2"/>`;
    }
    // Main circle
    svg += `<circle r="${r}" fill="#111827" stroke="${color}" stroke-width="1.5" filter="url(#shadow)"/>`;
    // Icon
    svg += `<text text-anchor="middle" dominant-baseline="central" font-size="${r > 14 ? 12 : 9}">${icon}</text>`;
    // Label
    const label = n.label || n.ip || n.mac || '';
    svg += `<text y="${r+12}" text-anchor="middle" font-size="9" fill="#9ca3af" font-family="JetBrains Mono,monospace">${label.length > 16 ? label.slice(0,14)+'..' : label}</text>`;
    // IP below label
    if(n.ip && n.type !== 'self') {
      svg += `<text y="${r+22}" text-anchor="middle" font-size="7" fill="#6b7280" font-family="JetBrains Mono,monospace">${n.ip}</text>`;
    }
    svg += `</g>`;
  });

  // Legend
  const legend = [
    {color:'#3b82f6',icon:'🛡',label:'This Device'},
    {color:'#f59e0b',icon:'📡',label:'Router'},
    {color:'#10b981',icon:'📶',label:'WiFi AP'},
    {color:'#60a5fa',icon:'💻',label:'Workstation'},
    {color:'#ff6b35',icon:'🖥',label:'Server'},
  ];
  let lx = 12, ly = H - 12;
  svg += `<g transform="translate(${lx},${ly})">`;
  svg += `<rect x="0" y="-70" width="120" height="72" rx="4" fill="#111827" stroke="#1f2937" opacity="0.9"/>`;
  legend.forEach((l, i) => {
    const yy = -60 + i*14;
    svg += `<circle cx="10" cy="${yy}" r="4" fill="${l.color}"/>`;
    svg += `<text x="20" y="${yy+3}" font-size="8" fill="#9ca3af">${l.label}</text>`;
  });
  svg += `</g>`;

  svg += '</svg>';
  el.innerHTML = svg;
}

async function showDeviceDetail(ip) {
  const detail = document.getElementById('topo-detail');
  const content = document.getElementById('device-detail-content');
  detail.classList.add('open');

  const devices = await fetch(API+'/sentient/devices').then(r=>r.json()).catch(()=>({devices:[]}));
  const device = (devices.devices||[]).find(d => d.ip === ip);
  if(!device) {
    content.innerHTML = '<p style="color:var(--text-muted)">Device not found</p>';
    return;
  }

  const services = (device.services||[]).map(s => `
    <div style="margin-bottom:8px;padding:8px;background:var(--bg-elevated);border-radius:4px;border-left:3px solid var(--accent)">
      <div style="font-size:12px;font-weight:600;color:var(--accent)">${s.port}/${s.protocol}</div>
      <div style="font-size:11px;color:var(--text-secondary)">${s.name} ${s.version?'v'+s.version:''}</div>
      ${s.banner?`<div style="font-size:10px;color:var(--text-muted);margin-top:2px;font-family:'JetBrains Mono',monospace">${s.banner}</div>`:''}
    </div>
  `).join('');

  const vulns = (device.vulnerabilities||[]).map(v => `
    <div style="margin-bottom:8px;padding:8px;background:var(--bg-elevated);border-radius:4px;border-left:3px solid var(--danger)">
      <div style="font-size:12px;font-weight:600"><span class="sev sev-${v.severity||'info'}">${(v.severity||'info').toUpperCase()}</span> ${v.name||'Unknown'}</div>
      <div style="font-size:11px;color:var(--text-secondary);margin-top:4px">${v.description||''}</div>
      ${v.cve?`<div style="font-size:10px;color:var(--text-muted);margin-top:2px">${v.cve}</div>`:''}
    </div>
  `).join('');

  content.innerHTML = `
    <div style="margin-bottom:16px">
      <div style="font-size:16px;font-weight:700;color:var(--accent);font-family:'JetBrains Mono',monospace">${device.ip}</div>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">${device.hostname||'No hostname'}</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
      <div style="padding:8px;background:var(--bg-elevated);border-radius:4px">
        <div style="font-size:10px;color:var(--text-muted)">MAC</div>
        <div style="font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--text-secondary)">${device.mac||'N/A'}</div>
      </div>
      <div style="padding:8px;background:var(--bg-elevated);border-radius:4px">
        <div style="font-size:10px;color:var(--text-muted)">OS</div>
        <div style="font-size:11px;color:var(--text-secondary)">${device.os_guess||'Unknown'}</div>
      </div>
      <div style="padding:8px;background:var(--bg-elevated);border-radius:4px">
        <div style="font-size:10px;color:var(--text-muted)">Type</div>
        <div style="font-size:11px;color:var(--text-secondary)"><span class="sev sev-${device.type==='router'?'high':'info'}">${device.type||'unknown'}</span></div>
      </div>
      <div style="padding:8px;background:var(--bg-elevated);border-radius:4px">
        <div style="font-size:10px;color:var(--text-muted)">Services</div>
        <div style="font-size:11px;color:var(--text-secondary)">${(device.services||[]).length} open</div>
      </div>
    </div>
    <div style="margin-bottom:12px;font-size:12px;font-weight:600;color:var(--text-primary)">Ports & Services</div>
    ${services||'<div style="color:var(--text-muted);font-size:12px">No services discovered</div>'}
    <div style="margin:12px 0 8px;font-size:12px;font-weight:600;color:var(--text-primary)">Vulnerabilities</div>
    ${vulns||'<div style="color:var(--text-muted);font-size:12px">No vulnerabilities found</div>'}
  `;
}

function closeDeviceDetail() {
  document.getElementById('topo-detail').classList.remove('open');
}

// Scan Page
async function renderScan() {
  const c = document.getElementById('content');
  c.innerHTML = `<div class="fade-in">
    <div class="tabs">
      <div class="tab active" onclick="showScanTab('nmap',this)">Nmap</div>
      <div class="tab" onclick="showScanTab('services',this)">Service Scan</div>
      <div class="tab" onclick="showScanTab('vuln',this)">Vuln Scan</div>
      <div class="tab" onclick="showScanTab('web',this)">Web Scan</div>
      <div class="tab" onclick="showScanTab('wifi',this)">WiFi Recon</div>
      <div class="tab" onclick="showScanTab('bluetooth',this)">Bluetooth</div>
      <div class="tab" onclick="showScanTab('custom',this)">Custom</div>
    </div>
    <div id="scan-form"></div>
    <div style="margin-top:16px">
      <div class="card">
        <div class="card-header">Command <span id="scan-cmd-preview" style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent);margin-left:8px"></span></div>
        <div class="card-body"><div class="terminal" id="scan-output">Ready. Select a scan type and click Run.</div></div>
      </div>
    </div>
  </div>`;
  showScanTab('nmap', document.querySelector('.tab'));
}

function showScanTab(type, el) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  const f = document.getElementById('scan-form');
  const forms = {
    nmap: `<div class="stats-grid" style="grid-template-columns:1fr 1fr 1fr">
      <div class="form-group"><label class="form-label">Target</label><input class="form-input" id="scan-target" placeholder="192.168.1.0/24" value="192.168.1.0/24"></div>
      <div class="form-group"><label class="form-label">Scan Type</label><select class="form-input" id="scan-type"><option value="-sn">Ping Sweep</option><option value="-sS -sV" selected>SYN + Version</option><option value="-sS -O">SYN + OS Detection</option><option value="-sU">UDP Scan</option><option value="-sA">ACK Scan</option></select></div>
      <div class="form-group"><label class="form-label">Ports</label><input class="form-input" id="scan-ports" placeholder="1-65535 or specific"></div>
    </div>
    <div class="form-group"><label class="form-label">Extra Flags</label><input class="form-input" id="scan-flags" placeholder="--script vuln -T4"></div>
    <button class="btn btn-primary" onclick="runScan('nmap')">▶ Run Nmap</button>`,
    services: `<div class="stats-grid" style="grid-template-columns:1fr 1fr"><div class="form-group"><label class="form-label">Target IP</label><input class="form-input" id="scan-target" placeholder="192.168.1.1"></div><div class="form-group"><label class="form-label">Intensity</label><select class="form-input" id="scan-intensity"><option value="3" selected>Normal</option><option value="5">Deep</option><option value="9">Aggressive</option></select></div></div><button class="btn btn-primary" onclick="runScan('service')">▶ Service Detection</button>`,
    vuln: `<div class="stats-grid" style="grid-template-columns:1fr 1fr"><div class="form-group"><label class="form-label">Target</label><input class="form-input" id="scan-target" placeholder="192.168.1.1"></div><div class="form-group"><label class="form-label">Script</label><select class="form-input" id="scan-script"><option value="vuln" selected>vuln</option><option value="vulners">vulners</option><option value="exploit">exploit</option></select></div></div><button class="btn btn-primary" onclick="runScan('vuln')">▶ Vulnerability Scan</button>`,
    web: `<div class="stats-grid" style="grid-template-columns:1fr 1fr"><div class="form-group"><label class="form-label">Target URL</label><input class="form-input" id="scan-target" placeholder="http://192.168.1.1"></div><div class="form-group"><label class="form-label">Tool</label><select class="form-input" id="scan-tool"><option value="nikto" selected>Nikto</option><option value="whatweb">WhatWeb</option><option value="dirb">Directory Brute Force</option></select></div></div><button class="btn btn-primary" onclick="runScan('web')">▶ Web Scan</button>`,
    wifi: `<div class="stats-grid" style="grid-template-columns:1fr 1fr"><div class="form-group"><label class="form-label">Interface</label><input class="form-input" id="scan-target" value="wlxc4e984dfb30f"></div><div class="form-group"><label class="form-label">Duration (sec)</label><input class="form-input" id="scan-duration" value="30" type="number"></div></div><button class="btn btn-primary" onclick="runScan('wifi')">▶ WiFi Recon</button>`,
    bluetooth: `<div class="form-group"><label class="form-label">Adapter</label><input class="form-input" id="scan-target" value="hci0"></div><button class="btn btn-primary" onclick="runScan('bluetooth')">▶ Bluetooth Scan</button>`,
    custom: `<div class="form-group"><label class="form-label">Command</label><input class="form-input" id="scan-custom-cmd" placeholder="nmap -sV 192.168.1.1"></div><button class="btn btn-primary" onclick="runScan('custom')">▶ Execute</button>`
  };
  f.innerHTML = forms[type]||forms.nmap;
}

async function runScan(type) {
  const output = document.getElementById('scan-output');
  const preview = document.getElementById('scan-cmd-preview');
  const target = document.getElementById('scan-target')?.value||'';

  let cmd = '';
  switch(type) {
    case 'nmap':
      const st = document.getElementById('scan-type')?.value||'-sS -sV';
      const ports = document.getElementById('scan-ports')?.value;
      const flags = document.getElementById('scan-flags')?.value||'';
      cmd = `nmap ${st} ${ports?'-p '+ports:''} ${flags} ${target}`;
      break;
    case 'service':
      cmd = `nmap -sV --version-intensity ${document.getElementById('scan-intensity')?.value||3} ${target}`;
      break;
    case 'vuln':
      cmd = `nmap --script ${document.getElementById('scan-script')?.value||'vuln'} ${target}`;
      break;
    case 'web':
      const tool = document.getElementById('scan-tool')?.value||'nikto';
      cmd = tool==='nikto'?`nikto -h ${target}`:tool==='whatweb'?`whatweb ${target}`:`dirb ${target}`;
      break;
    case 'wifi':
      cmd = `timeout ${document.getElementById('scan-duration')?.value||30} airodump-ng ${target} --write /tmp/wifi_scan`;
      break;
    case 'bluetooth':
      cmd = `hcitool -i ${target} scan`;
      break;
    case 'custom':
      cmd = document.getElementById('scan-custom-cmd')?.value||'';
      break;
  }
  if(!cmd) return;
  preview.textContent = '$ ' + cmd;
  output.innerHTML = '<span class="cmd">$ ' + cmd + '</span>\n<span class="warn">Executing...</span>';

  try {
    const res = await fetch(API+'/agents/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:'Execute: '+cmd, user_id:'ui'})
    });
    const data = await res.json();
    output.innerHTML = '<span class="cmd">$ ' + cmd + '</span>\n\n' + escapeHtml(data.content||'No output');
    output.scrollTop = output.scrollHeight;
  } catch(e) {
    output.innerHTML = '<span class="cmd">$ ' + cmd + '</span>\n<span class="err">Error: '+escapeHtml(e.message)+'</span>';
  }
}

// Findings Page
async function renderFindings() {
  const c = document.getElementById('content');
  c.innerHTML = '<div class="fade-in" id="findings-content"></div>';

  const [devices, tamagotchi] = await Promise.all([
    fetch(API+'/sentient/devices').then(r=>r.json()).catch(()=>({devices:[]})),
    fetch(API+'/tamagotchi/exploits').then(r=>r.json()).catch(()=>({exploits:[]}))
  ]);

  const devs = devices.devices||[];
  const vulns = [];
  devs.forEach(d => { (d.vulns||[]).forEach(v => vulns.push({...v, device:d.ip, hostname:d.hostname})); });

  const fc = document.getElementById('findings-content');
  const exploits = tamagotchi.exploits||[];

  const vulnRows = vulns.map(v => `<tr>
    <td><span class="sev sev-${v.severity||'info'}">${(v.severity||'info').toUpperCase()}</span></td>
    <td style="font-weight:500">${v.name||v.id||'Unknown'}</td>
    <td><code style="color:var(--accent);font-size:12px">${v.device}</code></td>
    <td>${v.port||'-'}</td>
    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${v.description||'-'}</td>
    <td><span class="status status-open">Open</span></td>
  </tr>`).join('');

  const exploitRows = exploits.map(e => `<tr>
    <td><span class="sev sev-${e.cvss>=9?'critical':e.cvss>=7?'high':e.cvss>=4?'medium':'low'}">${(e.cvss||0).toFixed(1)}</span></td>
    <td style="font-weight:500">${e.exploit_name||e.exploit||'Unknown'}</td>
    <td><code style="color:var(--accent);font-size:12px">${e.target}</code></td>
    <td>${e.service||'-'}</td>
    <td><span class="status status-${e.auth_status==='approved'?'fixed':e.auth_status==='denied'?'accepted':'open'}">${e.auth_status||'pending'}</span></td>
    <td><button class="btn btn-sm btn-primary" onclick="authExploit('${e.id}')">Authorize</button></td>
  </tr>`).join('');

  fc.innerHTML = `
    <div class="stats-grid" style="grid-template-columns:repeat(4,1fr)">
      <div class="stat-card"><div class="stat-label">Critical</div><div class="stat-value critical">${vulns.filter(v=>v.severity==='critical').length}</div></div>
      <div class="stat-card"><div class="stat-label">High</div><div class="stat-value high">${vulns.filter(v=>v.severity==='high').length}</div></div>
      <div class="stat-card"><div class="stat-label">Medium</div><div class="stat-value medium">${vulns.filter(v=>v.severity==='medium').length}</div></div>
      <div class="stat-card"><div class="stat-label">Low</div><div class="stat-value low">${vulns.filter(v=>v.severity==='low').length}</div></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header">Vulnerabilities <span style="color:var(--text-muted);font-weight:400;font-size:12px">${vulns.length} found</span></div>
      <div class="card-body table-wrap"><table><thead><tr><th>Sev</th><th>Name</th><th>Target</th><th>Port</th><th>Description</th><th>Status</th></tr></thead><tbody>${vulnRows||'<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px">No vulnerabilities found yet</td></tr>'}</tbody></table></div>
    </div>
    <div class="card">
      <div class="card-header">Exploit Queue <span style="color:var(--text-muted);font-weight:400;font-size:12px">${exploits.length} pending</span></div>
      <div class="card-body table-wrap"><table><thead><tr><th>CVSS</th><th>Exploit</th><th>Target</th><th>Service</th><th>Status</th><th>Action</th></tr></thead><tbody>${exploitRows||'<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px">No exploits queued</td></tr>'}</tbody></table></div>
    </div>`;
}

async function authExploit(id) {
  await fetch(API+'/tamagotchi/authorize', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({notification_id:id})});
  renderFindings();
}

// Tamagotchi Page (MAIN PAGE with Gamification)
async function renderTamagotchi() {
  const c = document.getElementById('content');
  c.innerHTML = '<div class="fade-in" id="tama-content"></div>';

  const [status, gamification, notifications, notifs, thinkLog] = await Promise.all([
    fetch(API+'/tamagotchi/status').then(r=>r.json()).catch(()=>({})),
    fetch(API+'/tamagotchi/gamification').then(r=>r.json()).catch(()=>({})),
    fetch(API+'/tamagotchi/notifications').then(r=>r.json()).catch(()=>({notifications:[]})),
    fetch(API+'/tamagotchi/notifications').then(r=>r.json()).catch(()=>({notifications:[]})),
    fetch(API+'/tamagotchi/thinking-log?limit=100').then(r=>r.json()).catch(()=>({entries:[]}))
  ]);

  const tc = document.getElementById('tama-content');
  const state = status.state||'idle';
  window.stateColors = {idle:'var(--text-muted)',scanning:'var(--accent)',mapping:'var(--info)',cracking:'var(--warning)',analyzing:'var(--success)',exploiting:'var(--danger)',alert:'var(--danger)',sleeping:'var(--text-muted)'};
  const stateColors = window.stateColors;

  // Mr. Robot ASCII Avatar — distinct per state
  window.avatarFrames = {
    idle: `<pre style="color:var(--text-muted)">
    ┌─────────────┐
    │  ░▒▓█ ELIOT █▓▒░  │
    │ ┌───────────┐ │
    │ │ ●     ● │ │
    │ │    ▼    │ │
    │ │  ───    │ │
    │ └───────────┘ │
    │   [ IDLE ]    │
    └─────────────┘</pre>`,
    scanning: `<pre style="color:var(--accent)">
    ┌─────────────┐
    │  ▓█ SCAN █▓  │
    │ ┌───────────┐ │
    │ │ ◉     ◉ │ │
    │ │  ◢██◣   │ │
    │ │  ───    │ │
    │ └───────────┘ │
    │  ╔═══╗       │
    │  ║ ◉ ║ scan  │
    │  ╚═══╝       │
    └─────────────┘</pre>`,
    analyzing: `<pre style="color:var(--success)">
    ┌─────────────┐
    │ ▓▓ ANALYZE ▓▓ │
    │ ┌───────────┐ │
    │ │ ◉     ◉ │ │
    │ │    ▼    │ │
    │ │ ═════   │ │
    │ └───────────┘ │
    │  ◌ ◌ ◌ ◌ ◌  │
    │  processing   │
    └─────────────┘</pre>`,
    exploiting: `<pre style="color:var(--danger)">
    ┌─────────────┐
    │ ██ EXPLOIT ██ │
    │ ┌───────────┐ │
    │ │ ▓     ▓ │ │
    │ │  ◢██◣   │ │
    │ │ ══╳══   │ │
    │ └───────────┘ │
    │  ⚡ BYPASS ⚡  │
    │  ▓▓▓▓▓▓▓▓▓  │
    └─────────────┘</pre>`,
    cracking: `<pre style="color:var(--warning)">
    ┌─────────────┐
    │ ░░ CRACK ░░  │
    │ ┌───────────┐ │
    │ │ ◉     ◉ │ │
    │ │    ▼    │ │
    │ │ ┌─┐┌─┐  │ │
    │ └───────────┘ │
    │  hashcat ...  │
    │  ▓▓▓░░░░░░░  │
    └─────────────┘</pre>`,
    alert: `<pre style="color:var(--danger)">
    ┌─────────────┐
    │ ⚠ ALERT! ⚠  │
    │ ┌───────────┐ │
    │ │ ◉     ◉ │ │
    │ │  ◢██◣   │ │
    │ │ ══╳══   │ │
    │ └───────────┘ │
    │  ▓▓▓▓▓▓▓▓▓  │
    │  !! DANGER !! │
    └─────────────┘</pre>`,
    sleeping: `<pre style="color:var(--text-muted)">
    ┌─────────────┐
    │   z Z z     │
    │ ┌───────────┐ │
    │ │ ─     ─ │ │
    │ │    ▼    │ │
    │ │  ───    │ │
    │ └───────────┘ │
    │   z Z z       │
    │  [ sleeping ]  │
    └─────────────┘</pre>`,
    mapping: `<pre style="color:var(--info)">
    ┌─────────────┐
    │ ◎ MAP ◎     │
    │ ┌───────────┐ │
    │ │ ◉     ◉ │ │
    │ │    ▼    │ │
    │ │ ╱─┼─╲   │ │
    │ └───────────┘ │
    │  ◉───◉──◉   │
    │  topology...  │
    └─────────────}</pre>`,
    reporting: `<pre style="color:var(--success)">
    ┌─────────────┐
    │ ░ REPORT ░   │
    │ ┌───────────┐ │
    │ │ ◉     ◉ │ │
    │ │    ▼    │ │
    │ │  ───    │ │
    │ └───────────┘ │
    │  ═══════════  │
    │  generating.. │
    └─────────────}</pre>`
  };

  const xpProgress = gamification.xp_progress||0;
  const xpPercent = Math.round(xpProgress*100);
  const levelName = gamification.level_name||'Script Kiddie';
  const level = gamification.level||1;
  const totalXp = gamification.total_xp||0;
  const xpToNext = gamification.xp_to_next||0;
  const nextLevelName = gamification.next_level_name||'Unknown';

  // Achievements grid
  const allAchievements = gamification.achievements_available||14;
  const unlockedAchievements = gamification.achievements||[];
  const achievementDefs = {
    first_scan: {name:'First Steps',desc:'Complete your first scan',icon:'🔍'},
    first_device: {name:'Network Explorer',desc:'Discover your first device',icon:'📡'},
    first_vuln: {name:'Bug Finder',desc:'Find your first vulnerability',icon:'🐛'},
    first_exploit: {name:'Exploit Artist',desc:'Execute your first exploit',icon:'💥'},
    first_crack: {name:'Password Hunter',desc:'Complete your first crack session',icon:'🔐'},
    ten_devices: {name:'Network Mapper',desc:'Discover 10 devices',icon:'🗺️'},
    ten_vulns: {name:'Vuln Collector',desc:'Find 10 vulnerabilities',icon:'📋'},
    hundred_xp: {name:'Rising Star',desc:'Earn 100 XP total',icon:'⭐'},
    thousand_xp: {name:'Dedicated Hacker',desc:'Earn 1000 XP total',icon:'🌟'},
    level_5: {name:'Getting Serious',desc:'Reach level 5',icon:'📈'},
    level_10: {name:'Pro Pentester',desc:'Reach level 10',icon:'🏆'},
    night_owl: {name:'Night Owl',desc:'Run a scan between 2-5 AM',icon:'🦉'},
    full_network: {name:'Network Dominator',desc:'Map an entire /24 subnet',icon:'🌐'},
    stealth_master: {name:'Ghost',desc:'Complete 10 scans without detection',icon:'👻'}
  };

  const unlockedKeys = unlockedAchievements.map(a => a.key||'');
  let achievementHtml = '';
  for(const [key, ach] of Object.entries(achievementDefs)) {
    const unlocked = unlockedKeys.includes(key);
    achievementHtml += `
      <div class="achievement-card ${unlocked?'unlocked':'achievement-locked'}">
        <div class="achievement-icon">${ach.icon}</div>
        <div class="achievement-name">${ach.name}</div>
        <div class="achievement-desc">${ach.desc}</div>
      </div>`;
  }

  // Recent events
  const recentEvents = (gamification.recent_events||[]).slice(0,10);
  const eventsHtml = recentEvents.map(e => {
    const time = new Date(e.timestamp*1000).toLocaleTimeString('en-US',{hour12:false});
    let typeClass = 'info';
    let msg = '';
    if(e.type==='xp') { typeClass='xp'; msg=`+${e.xp} XP for ${e.action}${e.detail?' ('+e.detail+')':''}`; }
    else if(e.type==='achievement') { typeClass='achievement'; msg=`🏆 ${e.name}: ${e.desc}`; }
    else if(e.type==='penalty') { typeClass='penalty'; msg=`⚠️ ${e.action}: ${e.reason} (${e.xp} XP)`; }
    else if(e.type==='level_up') { typeClass='level_up'; msg=`🎉 Level Up! Now: ${e.name} (Level ${e.level})`; }
    return `<div class="log-entry"><span class="log-time">${time}</span><span class="log-type ${typeClass}">${e.type}</span><span class="log-message">${escapeHtml(msg)}</span></div>`;
  }).join('');

  // Mistakes/learning
  const mistakes = gamification.mistakes||{};
  const streaks = gamification.streaks||{};

  // Notifications
  const pendingNotifs = (notifs.notifications||[]).filter(n => n.needs_auth && n.auth_status==='pending');
  const notifRows = pendingNotifs.slice(0,5).map(n => `
    <div style="margin-bottom:8px;padding:10px;background:var(--bg-elevated);border-radius:6px;border-left:3px solid var(--warning)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:12px;font-weight:600">${n.title}</span>
        <span class="sev sev-${n.severity||'info'}">${(n.severity||'info').toUpperCase()}</span>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:4px">${n.message}</div>
      <div style="margin-top:8px;display:flex;gap:6px">
        <button class="btn btn-sm btn-primary" onclick="authNotif('${n.id}')">Approve</button>
        <button class="btn btn-sm" onclick="denyNotif('${n.id}')">Deny</button>
      </div>
    </div>
  `).join('');

  tc.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <!-- Left Column: Avatar + Gamification -->
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header">
            Tamagotchi Agent ${state==='analyzing'||state==='scanning'?'<span class="pulse" style="color:var(--accent)">●</span>':''}
            <div style="display:flex;gap:6px">
              ${status.running?
                (status.paused?
                  `<button class="btn btn-sm btn-primary" onclick="resumeTama()">▶ Resume</button>`:
                  `<button class="btn btn-sm" onclick="pauseTama()">⏸ Pause</button>`
                ):
                `<button class="btn btn-sm btn-primary" onclick="startTama()">▶ Start</button>`
              }
              <button class="btn btn-sm btn-danger" onclick="stopTama()">⏹ Stop</button>
            </div>
          </div>
          <div class="card-body">
            <div class="avatar-container avatar-anim-${state}" id="avatar-container">
              <div class="avatar-ascii" id="avatar-live">${(window.avatarFrames||{})[state]||(window.avatarFrames||{}).idle}</div>
              <div class="avatar-state" id="avatar-state-live" style="color:${stateColors[state]||'var(--text-muted)'}">${state}</div>
              <div id="avatar-thought" style="margin-top:8px;padding:8px 12px;background:var(--bg-elevated);border-radius:6px;font-size:11px;color:var(--text-secondary);font-family:'JetBrains Mono',monospace;max-width:280px;text-align:center;min-height:20px">
                ${status.current_thought||'...'}
              </div>
              ${status.current_phase && status.current_phase!=='idle'?`
              <div style="margin-top:8px;width:100%">
                <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-bottom:4px">
                  <span>${status.current_phase.replace(/_/g,' ')}</span>
                  <span>${status.phase_progress?.progress||0}%</span>
                </div>
                <div style="height:4px;background:var(--bg-elevated);border-radius:2px;overflow:hidden">
                  <div style="height:100%;width:${status.phase_progress?.progress||0}%;background:var(--accent);border-radius:2px;transition:width 0.5s"></div>
                </div>
              </div>
              `:''}
            </div>
            <div style="text-align:center;margin-top:12px">
              <div style="font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--accent)">Level ${level}</div>
              <div style="font-size:14px;color:var(--text-secondary)">${levelName}</div>
            </div>
          </div>
        </div>

        <!-- Phase Timeline Card -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-header">Phase Timeline <span style="color:var(--text-muted);font-weight:400;font-size:11px" id="phase-count"></span></div>
          <div class="card-body" style="padding:8px 12px">
            <div id="phase-timeline" style="display:flex;flex-direction:column;gap:2px">
              ${(()=>{
                const phases = [
                  {id:'network_discovery',name:'Network Discovery',icon:'🔍'},
                  {id:'wifi_recon',name:'WiFi Recon',icon:'📡'},
                  {id:'host_discovery',name:'Host Discovery',icon:'🖥️'},
                  {id:'service_analysis',name:'Service Analysis',icon:'⚙️'},
                  {id:'os_detection',name:'OS Detection',icon:'🏷️'},
                  {id:'vuln_scanning',name:'Vuln Scanning',icon:'🛡️'},
                  {id:'topology',name:'Topology',icon:'🗺️'},
                  {id:'osint',name:'OSINT',icon:'🌐'},
                  {id:'bluetooth',name:'Bluetooth',icon:'📶'},
                  {id:'handshake',name:'Handshake',icon:'🔑'},
                  {id:'web_testing',name:'Web Testing',icon:'🌍'},
                  {id:'auto_exploit',name:'Auto-Exploit',icon:'⚡'},
                  {id:'exploitation',name:'Exploitation',icon:'💥'},
                  {id:'post_exploit',name:'Post-Exploit',icon:'🏴'},
                  {id:'learning',name:'Learning',icon:'🧠'},
                  {id:'reporting',name:'Reporting',icon:'📊'},
                  {id:'idle',name:'Idle',icon:'💤'},
                ];
                const cp = status.current_phase||'idle';
                const ci = phases.findIndex(p=>p.id===cp);
                return phases.map((p,i)=>{
                  let style='opacity:0.35';
                  let badge='○';
                  if(i<ci){style='opacity:0.7';badge='✓';}
                  else if(i===ci){style='color:var(--accent);font-weight:600;opacity:1';badge='●';}
                  return `<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:11px;${style}" class="phase-row" data-phase="${p.id}">
                    <span style="width:16px;text-align:center">${badge}</span>
                    <span>${p.icon}</span>
                    <span style="flex:1">${p.name}</span>
                    ${i===status.phase_progress?.progress?'':''}
                  </div>`;
                }).join('');
              })()}
            </div>
            ${status.current_phase && status.current_phase!=='idle'?`
            <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
              <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-bottom:3px">
                <span>Current: ${status.current_phase.replace(/_/g,' ')}</span>
                <span id="phase-pct">${status.phase_progress?.progress||0}%</span>
              </div>
              <div style="height:3px;background:var(--bg-elevated);border-radius:2px;overflow:hidden">
                <div id="phase-bar" style="height:100%;width:${status.phase_progress?.progress||0}%;background:var(--accent);border-radius:2px;transition:width 0.5s"></div>
              </div>
            </div>`:''}
          </div>
        </div>

        <!-- Think Log Card -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-header">Think Log <span style="color:var(--text-muted);font-weight:400;font-size:11px" id="think-count">${(thinkLog.entries||[]).length} entries</span></div>
          <div class="card-body" style="padding:0">
            <div id="think-log" style="max-height:240px;overflow-y:auto;font-size:11px;font-family:'JetBrains Mono',monospace;padding:8px 12px;scroll-behavior:smooth">
              ${(thinkLog.entries||[]).slice(0,50).map(e=>{
                const age = Date.now()-new Date(e.timestamp*1000).getTime();
                const ts = age<60000?Math.floor(age/1000)+'s':age<3600000?Math.floor(age/60000)+'m':Math.floor(age/3600000)+'h';
                const sc = stateColors[e.state]||'var(--text-muted)';
                return `<div style="padding:3px 0;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:flex-start">
                  <span style="color:var(--text-muted);white-space:nowrap;min-width:28px">${ts}</span>
                  <span style="color:${sc};white-space:nowrap;min-width:14px">[${e.state||'?'}]</span>
                  <span style="color:var(--text-secondary);word-break:break-word">${e.thought||''}</span>
                </div>`;
              }).join('')}
            </div>
          </div>
        </div>

        <div class="card" style="margin-bottom:16px">
          <div class="card-header">Experience Points</div>
          <div class="card-body">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
              <span style="font-size:12px;color:var(--text-secondary)">${totalXp} XP</span>
              <span style="font-size:12px;color:var(--text-secondary)">${xpToNext} XP to ${nextLevelName}</span>
            </div>
            <div class="xp-bar-container">
              <div class="xp-bar-fill" style="width:${xpPercent}%"></div>
              <div class="xp-bar-text">${xpPercent}%</div>
            </div>
            <div class="streak-container">
              <div class="streak-item">
                <div class="streak-value">${streaks.scans||0}</div>
                <div class="streak-label">Scans</div>
              </div>
              <div class="streak-item">
                <div class="streak-value">${streaks.devices||0}</div>
                <div class="streak-label">Devices</div>
              </div>
              <div class="streak-item">
                <div class="streak-value">${streaks.vulns||0}</div>
                <div class="streak-label">Vulns</div>
              </div>
              <div class="streak-item">
                <div class="streak-value">${streaks.exploits||0}</div>
                <div class="streak-label">Exploits</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">Achievements <span style="color:var(--text-muted);font-weight:400;font-size:12px">${unlockedKeys.length}/${Object.keys(achievementDefs).length}</span></div>
          <div class="card-body">
            <div class="achievement-grid">${achievementHtml}</div>
          </div>
        </div>
      </div>

      <!-- Right Column: Notifications + Events + Learning -->
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header">Pending Authorizations <span style="color:var(--text-muted);font-weight:400;font-size:12px">${pendingNotifs.length}</span></div>
          <div class="card-body">
            ${notifRows||'<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px">No pending authorizations</div>'}
          </div>
        </div>

        <div class="card" style="margin-bottom:16px">
          <div class="card-header">Recent Activity</div>
          <div class="card-body" style="padding:0;max-height:300px;overflow-y:auto">
            ${eventsHtml||'<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:30px">No activity yet. Start a scan to earn XP!</div>'}
          </div>
        </div>

        <div class="card">
          <div class="card-header">Learning Data</div>
          <div class="card-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
              <div style="padding:12px;background:var(--bg-elevated);border-radius:6px;text-align:center">
                <div style="font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--accent)">${mistakes.total_mistakes||0}</div>
                <div style="font-size:10px;color:var(--text-muted)">Total Mistakes</div>
              </div>
              <div style="padding:12px;background:var(--bg-elevated);border-radius:6px;text-align:center">
                <div style="font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--success)">${Math.round((mistakes.learning_rate||0)*100)}%</div>
                <div style="font-size:10px;color:var(--text-muted)">Learning Rate</div>
              </div>
            </div>
            <div style="font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:8px">Mistake Categories</div>
            <div style="font-size:12px;color:var(--text-secondary)">
              ${Object.entries(mistakes.categories||{}).map(([k,v])=>`<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border)"><span>${k}</span><span style="color:var(--danger)">${v}</span></div>`).join('')||'No mistakes recorded yet'}
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// Intel Page (Chat)
async function renderIntel() {
  const c = document.getElementById('content');
  c.innerHTML = `<div class="fade-in"><div class="chat-container">
    <div class="chat-messages" id="chat-messages"></div>
    <div id="chat-suggestions"></div>
    <div class="chat-input-wrap">
      <textarea class="chat-input" id="chat-input" placeholder="Ask ELIOT anything..." rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat()}"></textarea>
      <button class="btn btn-primary" onclick="sendChat()">Send</button>
    </div>
  </div></div>`;

  renderChatMessages();
  loadSuggestions();
}

function renderChatMessages() {
  const el = document.getElementById('chat-messages');
  if(!el) return;
  el.innerHTML = chatMessages.map(m => `
    <div class="chat-msg ${m.role}">
      <div class="bubble">${escapeHtml(m.content)}</div>
      <div class="meta">${m.role==='user'?'You':'ELIOT'} · ${m.time||''}</div>
    </div>`).join('');
  el.scrollTop = el.scrollHeight;
}

async function loadSuggestions() {
  const el = document.getElementById('chat-suggestions');
  try {
    const res = await fetch(API+'/tamagotchi/suggestions');
    const data = await res.json();
    el.innerHTML = `<div class="suggestions">${(data.suggestions||[]).map(s=>`<div class="suggestion" onclick="document.getElementById('chat-input').value='${(s.text||s).replace(/'/g,"\\'")}';sendChat()">${s.text||s}</div>`).join('')}</div>`;
  } catch(e) { el.innerHTML=''; }
}

let chatWaiting = false;

async function sendChat() {
  if(chatWaiting) return;
  const input = document.getElementById('chat-input');
  const sendBtn = document.querySelector('.chat-input-wrap .btn-primary');
  const msg = input.value.trim();
  if(!msg) return;
  input.value = '';

  chatWaiting = true;
  input.disabled = true;
  input.placeholder = 'Waiting for response...';
  if(sendBtn) sendBtn.disabled = true;

  chatMessages.push({role:'user', content:msg, time:new Date().toLocaleTimeString('en-US',{hour12:false})});
  renderChatMessages();

  const placeholder = {role:'assistant', content:'...', time:new Date().toLocaleTimeString('en-US',{hour12:false})};
  chatMessages.push(placeholder);
  renderChatMessages();

  try {
    const res = await fetch(API+'/agents/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg, user_id:'ui'})});
    const data = await res.json();
    placeholder.content = data.content || 'No response';
    placeholder.time = new Date().toLocaleTimeString('en-US',{hour12:false});
  } catch(e) {
    placeholder.content = 'Error: '+e.message;
  }

  chatWaiting = false;
  input.disabled = false;
  input.placeholder = 'Ask ELIOT anything...';
  if(sendBtn) sendBtn.disabled = false;
  input.focus();
  renderChatMessages();
  loadSuggestions();
}

// Knowledge Page
async function renderKnowledge() {
  const c = document.getElementById('content');
  c.innerHTML = '<div class="fade-in" id="knowledge-content"></div>';

  const [knowledge] = await Promise.all([
    fetch(API+'/tamagotchi/knowledge').then(r=>r.json()).catch(()=>({entries:[],stats:{}})),
  ]);

  const stats = knowledge.stats||{};
  const entries = knowledge.entries||[];

  const categories = {};
  entries.forEach(e => {
    const cat = e.category||'unknown';
    if(!categories[cat]) categories[cat]=[];
    categories[cat].push(e);
  });

  let categoryTabs = '';
  let categoryContent = '';
  for(const [cat, items] of Object.entries(categories)) {
    categoryTabs += `<div class="tab" onclick="showKnowledgeCategory('${cat}',this)">${cat}</div>`;
    const rows = items.slice(0,20).map(e => `<tr>
      <td style="font-weight:500;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${e.key||'-'}</td>
      <td style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${typeof e.value==='object'?JSON.stringify(e.value).slice(0,100):e.value}</td>
      <td style="font-size:11px;color:var(--text-muted)">${e.timestamp?new Date(e.timestamp*1000).toLocaleDateString():'-'}</td>
    </tr>`).join('');
    categoryContent += `<div id="cat-${cat}" style="display:none"><div class="card"><div class="card-body table-wrap"><table><thead><tr><th>Key</th><th>Value</th><th>Date</th></tr></thead><tbody>${rows}</tbody></table></div></div></div>`;
  }

  document.getElementById('knowledge-content').innerHTML = `
    <div class="stats-grid" style="grid-template-columns:repeat(4,1fr)">
      <div class="stat-card"><div class="stat-label">Total Entries</div><div class="stat-value accent">${entries.length}</div></div>
      <div class="stat-card"><div class="stat-label">Categories</div><div class="stat-value success">${Object.keys(categories).length}</div></div>
      <div class="stat-card"><div class="stat-label">Devices</div><div class="stat-value medium">${stats.device||0}</div></div>
      <div class="stat-card"><div class="stat-label">Services</div><div class="stat-value info">${stats.service_version||0}</div></div>
    </div>
    <div class="tabs" id="knowledge-tabs">${categoryTabs}</div>
    <div id="knowledge-entries">${categoryContent}</div>
    <div class="card" style="margin-top:16px">
      <div class="card-header">All Knowledge</div>
      <div class="card-body table-wrap"><table><thead><tr><th>Key</th><th>Value</th><th>Date</th></tr></thead><tbody>${entries.slice(0,50).map(e=>`<tr><td style="font-weight:500;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${e.key||'-'}</td><td style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${typeof e.value==='object'?JSON.stringify(e.value).slice(0,100):e.value}</td><td style="font-size:11px;color:var(--text-muted)">${e.timestamp?new Date(e.timestamp*1000).toLocaleDateString():'-'}</td></tr>`).join('')||'<tr><td colspan="3" style="text-align:center;color:var(--text-muted);padding:30px">Knowledge base empty. Using LLM during chat builds the index.</td></tr>'}</tbody></table></div>
    </div>`;
}

function showKnowledgeCategory(cat, el) {
  document.querySelectorAll('#knowledge-tabs .tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  document.querySelectorAll('[id^="cat-"]').forEach(d=>d.style.display='none');
  const catEl = document.getElementById('cat-'+cat);
  if(catEl) catEl.style.display='block';
}

// Logs Page
async function renderLogs() {
  const c = document.getElementById('content');
  c.innerHTML = `<div class="fade-in">
    <div class="tabs">
      <div class="tab active" onclick="showLogTab('events',this)">Events</div>
      <div class="tab" onclick="showLogTab('system',this)">System</div>
      <div class="tab" onclick="showLogTab('scans',this)">Scans</div>
    </div>
    <div id="logs-content"></div>
  </div>`;
  showLogTab('events', document.querySelector('.tab'));
}

async function showLogTab(type, el) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  const lc = document.getElementById('logs-content');

  if(type==='events') {
    const data = await fetch(API+'/tamagotchi/events?limit=100').then(r=>r.json()).catch(()=>({events:[]}));
    const events = data.events||[];
    const html = events.reverse().map(e => {
      const time = new Date(e.timestamp*1000).toLocaleString('en-US',{hour12:false});
      let typeClass = 'info';
      let msg = '';
      if(e.type==='xp') { typeClass='xp'; msg=`+${e.xp} XP for ${e.action}${e.detail?' ('+e.detail+')':''}`; }
      else if(e.type==='achievement') { typeClass='achievement'; msg=`🏆 ${e.name}: ${e.desc}`; }
      else if(e.type==='penalty') { typeClass='penalty'; msg=`⚠️ ${e.action}: ${e.reason} (${e.xp} XP)`; }
      else if(e.type==='level_up') { typeClass='level_up'; msg=`🎉 Level Up! Now: ${e.name} (Level ${e.level})`; }
      return `<div class="log-entry"><span class="log-time">${time}</span><span class="log-type ${typeClass}">${e.type}</span><span class="log-message">${escapeHtml(msg)}</span></div>`;
    }).join('');
    lc.innerHTML = `<div class="card"><div class="card-header">Event Log <span style="color:var(--text-muted);font-weight:400;font-size:12px">${events.length} events</span></div><div class="card-body" style="padding:0">${html||'<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:30px">No events recorded yet</div>'}</div></div>`;
  }
  else if(type==='system') {
    const data = await fetch(API+'/tamagotchi/status').then(r=>r.json()).catch(()=>({}));
    lc.innerHTML = `<div class="card"><div class="card-header">System Status</div><div class="card-body"><pre style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-secondary);white-space:pre-wrap">${JSON.stringify(data,null,2)}</pre></div></div>`;
  }
  else if(type==='scans') {
    const data = await fetch(API+'/sentient/status').then(r=>r.json()).catch(()=>({}));
    lc.innerHTML = `<div class="card"><div class="card-header">Scan Engine Status</div><div class="card-body"><pre style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-secondary);white-space:pre-wrap">${JSON.stringify(data,null,2)}</pre></div></div>`;
  }
}

// Documents Page
async function renderDocuments() {
  const c = document.getElementById('content');
  c.innerHTML = `<div class="fade-in">
    <div class="stats-grid" style="grid-template-columns:repeat(3,1fr)">
      <div class="stat-card">
        <div class="stat-label">Reports</div>
        <div class="stat-value accent">0</div>
        <div class="stat-sub">generated</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Findings</div>
        <div class="stat-value medium">0</div>
        <div class="stat-sub">documented</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Exports</div>
        <div class="stat-value success">0</div>
        <div class="stat-sub">downloaded</div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">Reports</div>
      <div class="card-body">
        <div style="text-align:center;padding:40px;color:var(--text-muted)">
          <div style="font-size:48px;margin-bottom:16px">📄</div>
          <div style="font-size:14px;font-weight:600;color:var(--text-secondary);margin-bottom:8px">No Reports Yet</div>
          <div style="font-size:12px;max-width:400px;margin:0 auto">Run scans and discover devices to generate reports. Reports will be available for download here.</div>
          <button class="btn btn-primary" style="margin-top:16px" onclick="showPage('scan')">Start Scanning →</button>
        </div>
      </div>
    </div>
  </div>`;
}

// Settings Page
async function renderSettings() {
  const c = document.getElementById('content');
  c.innerHTML = `<div class="fade-in">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div class="card">
        <div class="card-header">Stealth Engine</div>
        <div class="card-body">
          <div class="form-group"><label class="form-label">Active</label><select class="form-input" id="stealth-active"><option value="true">Yes</option><option value="false">No</option></select></div>
          <div class="form-group"><label class="form-label">Default Profile</label><select class="form-input" id="stealth-profile"><option value="silent">Silent</option><option value="low">Low</option><option value="normal" selected>Normal</option><option value="aggressive">Aggressive</option></select></div>
          <div class="form-group"><label class="form-label">MAC Randomization</label><select class="form-input" id="stealth-mac"><option value="false">Disabled</option><option value="true">Enabled</option></select></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">Sentient Engine</div>
        <div class="card-body">
          <div class="form-group"><label class="form-label">Auto Scan</label><select class="form-input" id="sentient-enabled"><option value="true">Enabled</option><option value="false">Disabled</option></select></div>
          <div class="form-group"><label class="form-label">Scan Interval (sec)</label><input class="form-input" id="sentient-interval" value="300" type="number"></div>
          <div class="form-group"><label class="form-label">WiFi Interface</label><input class="form-input" id="sentient-wifi" value="wlxc4e984dfb30f"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">Tamagotchi Engine</div>
        <div class="card-body">
          <div class="form-group"><label class="form-label">Auto Scan</label><select class="form-input" id="tama-enabled"><option value="true">Enabled</option><option value="false">Disabled</option></select></div>
          <div class="form-group"><label class="form-label">Scan Interval (sec)</label><input class="form-input" id="tama-interval" value="600" type="number"></div>
          <div class="form-group"><label class="form-label">Auto Exploit</label><select class="form-input" id="tama-exploit"><option value="false">Disabled (require auth)</option><option value="true">Enabled</option></select></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">Quick Actions</div>
        <div class="card-body">
          <button class="btn btn-primary" style="width:100%;margin-bottom:8px" onclick="triggerFullScan()">🔍 Full Network Scan</button>
          <button class="btn" style="width:100%;margin-bottom:8px" onclick="fetch(API+'/tamagotchi/clear-notifications',{method:'POST'})">🗑 Clear Old Notifications</button>
          <button class="btn btn-danger" style="width:100%" onclick="if(confirm('Stop all engines?')){fetch(API+'/sentient/stop',{method:'POST'});fetch(API+'/tamagotchi/stop',{method:'POST'})}">⏹ Stop All Engines</button>
        </div>
      </div>
    </div>
  </div>`;
}

async function triggerFullScan() {
  document.getElementById('page-title').innerHTML = 'Scan <span class="breadcrumb">Running...</span>';
  try {
    await fetch(API+'/sentient/scan', {method:'POST'});
    setTimeout(()=>showPage('overview'), 1000);
  } catch(e) { alert('Scan failed: '+e.message); }
}

// Badges
function updateBadges(devices, vulns) {
  const nd = document.getElementById('nav-devices');
  const nv = document.getElementById('nav-vulns');
  if(nd) { nd.textContent=devices; nd.style.display=devices?'inline':'none'; }
  if(nv) { nv.textContent=vulns; nv.style.display=vulns?'inline':'none'; }
}

// WebSocket for live updates — drives avatar rendering
let avatarWSState = {};
function connectWS() {
  try {
    const proto = location.protocol==='https:'?'wss':'ws';
    ws = new WebSocket(proto+'://'+location.host+'/avatar/ws');
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        avatarWSState = d;
        if(d.state) {
          const dot = document.getElementById('status-dot');
          const txt = document.getElementById('status-text');
          if(dot) dot.className = 'status-dot ' + (d.state==='error'?'off':'on');
          if(txt) txt.textContent = d.state;
        }
        // Live avatar update from WebSocket
        const avatarEl = document.getElementById('avatar-live');
        const avatarCt = document.getElementById('avatar-container');
        if(avatarEl && d.state) {
          const f = (window.avatarFrames||{})[d.state] || (window.avatarFrames||{}).idle;
          avatarEl.innerHTML = f;
          // Update animation class on container
          if(avatarCt) {
            avatarCt.className = 'avatar-container avatar-anim-' + d.state;
          }
          const sc = document.getElementById('avatar-state-live');
          if(sc) { sc.textContent = d.state; sc.style.color = stateColors[d.state]||'var(--text-muted)'; }
        }
        // Live thought from text_display
        const thEl = document.getElementById('avatar-thought');
        if(thEl && d.text_display) thEl.textContent = d.text_display;
      } catch(ex){}
    };
    ws.onclose = () => setTimeout(connectWS, 5000);
  } catch(e) {}
}

// Tamagotchi WebSocket — live phase transitions + think messages
let tamaWS = null;
let tamaThinkBuffer = [];
function connectTamaWS() {
  try {
    const proto = location.protocol==='https:'?'wss':'ws';
    tamaWS = new WebSocket(proto+'://'+location.host+'/tamagotchi/ws');
    tamaWS.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if(d.type === 'tama_think' && d.data) {
          // Prepend to think log
          const logEl = document.getElementById('think-log');
          if(logEl) {
            const age = Date.now()-new Date(d.data.timestamp*1000).getTime();
            const ts = age<60000?Math.floor(age/1000)+'s':age<3600000?Math.floor(age/60000)+'m':Math.floor(age/3600000)+'h';
            const sc = (window.stateColors||{})[d.data.state]||'var(--text-muted)';
            const html = `<div style="padding:3px 0;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:flex-start" class="think-entry">
              <span style="color:var(--text-muted);white-space:nowrap;min-width:28px">${ts}</span>
              <span style="color:${sc};white-space:nowrap;min-width:14px">[${d.data.state||'?'}]</span>
              <span style="color:var(--text-secondary);word-break:break-word">${d.data.thought||''}</span>
            </div>`;
            logEl.insertAdjacentHTML('afterbegin', html);
            // Keep max 80 entries in DOM
            while(logEl.children.length > 80) logEl.removeChild(logEl.lastChild);
          }
          // Update thought bubble
          const thEl = document.getElementById('avatar-thought');
          if(thEl && d.data.thought) thEl.textContent = d.data.thought;
          // Update count
          const cnt = document.getElementById('think-count');
          if(cnt) cnt.textContent = logEl ? logEl.children.length+' entries' : '';
        }
        if(d.type === 'tama_phase' && d.data) {
          // Update phase timeline
          updatePhaseTimeline(d.data.phase, d.data.status);
        }
      } catch(ex){}
    };
    tamaWS.onclose = () => setTimeout(connectTamaWS, 5000);
  } catch(e) {}
}

function updatePhaseTimeline(currentPhase, status) {
  const rows = document.querySelectorAll('.phase-row');
  const phases = ['network_discovery','wifi_recon','host_discovery','service_analysis','os_detection','vuln_scanning','topology','osint','bluetooth','handshake','web_testing','auto_exploit','exploitation','post_exploit','learning','reporting','idle'];
  const ci = phases.indexOf(currentPhase);
  rows.forEach((row,i) => {
    const badge = row.querySelector('span:first-child');
    if(i < ci) { row.style.opacity='0.7'; if(badge) badge.textContent='✓'; }
    else if(i === ci) { row.style.opacity='1'; row.style.color='var(--accent)'; row.style.fontWeight='600'; if(badge) badge.textContent='●'; }
    else { row.style.opacity='0.35'; row.style.color=''; row.style.fontWeight=''; if(badge) badge.textContent='○'; }
  });
}

// Tamagotchi Controls
async function startTama() {
  await fetch(API+'/tamagotchi/start', {method:'POST'});
  setTimeout(()=>showPage('tamagotchi'), 500);
}
async function pauseTama() {
  await fetch(API+'/tamagotchi/pause', {method:'POST'});
  setTimeout(()=>showPage('tamagotchi'), 500);
}
async function resumeTama() {
  await fetch(API+'/tamagotchi/resume', {method:'POST'});
  setTimeout(()=>showPage('tamagotchi'), 500);
}
async function stopTama() {
  if(!confirm('Stop the tamagotchi agent?')) return;
  await fetch(API+'/tamagotchi/stop', {method:'POST'});
  setTimeout(()=>showPage('tamagotchi'), 500);
}

// Utils
function escapeHtml(s) {
  if(!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Init
connectWS();
connectTamaWS();
showPage('tamagotchi');
setInterval(()=>{ if(currentPage==='tamagotchi') renderTamagotchi(); }, 5000);

// Map auto-refresh with interaction-aware freeze
let mapFrozen = false;
let mapUnfreezeTimer = null;
let mapData = null;

function freezeMap() {
  mapFrozen = true;
  const badge = document.getElementById('map-freeze-badge');
  if(badge) badge.style.display = 'flex';
  clearTimeout(mapUnfreezeTimer);
  mapUnfreezeTimer = setTimeout(()=>{ mapFrozen = false; const b=document.getElementById('map-freeze-badge'); if(b) b.style.display='none'; }, 10000);
}

function unfreezeMap() {
  mapFrozen = false;
  clearTimeout(mapUnfreezeTimer);
  const badge = document.getElementById('map-freeze-badge');
  if(badge) badge.style.display = 'none';
  renderMap();
}

async function fetchMapData() {
  const [topology, devices, wifi, tamaStatus] = await Promise.all([
    fetch(API+'/sentient/topology').then(r=>r.json()).catch(()=>({nodes:[],edges:[]})),
    fetch(API+'/sentient/devices').then(r=>r.json()).catch(()=>({devices:[]})),
    fetch(API+'/sentient/wifi').then(r=>r.json()).catch(()=>({access_points:[]})),
    fetch(API+'/tamagotchi/status').then(r=>r.json()).catch(()=>({})),
  ]);
  mapData = {topology, devices, wifi, tamaStatus};
  return mapData;
}

function updateMapStatusOnly() {
  if(!mapData || currentPage !== 'map') return;
  const {topology, devices, wifi, tamaStatus} = mapData;
  const devs = devices.devices || [];
  const nodeCount = (topology.nodes||[]).length;
  const edgeCount = (topology.edges||[]).length;
  const phase = tamaStatus.current_phase || 'idle';
  const thought = tamaStatus.current_thought || '...';
  const isScanning = tamaStatus.state === 'scanning';
  const stateColors2 = {idle:'var(--text-muted)',scanning:'var(--accent)',mapping:'var(--info)',cracking:'var(--warning)',analyzing:'var(--success)',exploiting:'var(--danger)',alert:'var(--danger)',sleeping:'var(--text-muted)'};
  const bar = document.getElementById('map-status-bar');
  if(bar) {
    const freezeBadge = document.getElementById('map-freeze-badge');
    const wasFrozen = mapFrozen;
    bar.innerHTML = `
    <div style="width:8px;height:8px;border-radius:50%;background:${isScanning?'var(--accent)':'var(--text-muted)'};${isScanning?'animation:pulse 1.5s infinite':''}"></div>
    <span style="font-size:12px;font-weight:600;color:${stateColors2[tamaStatus.state]||'var(--text-muted)'}">${tamaStatus.state||'unknown'}</span>
    <span style="font-size:11px;color:var(--text-muted)">|</span>
    <span style="font-size:11px;color:var(--text-secondary)">${nodeCount} nodes · ${edgeCount} edges · ${devs.length} devices · ${(wifi.access_points||[]).length} APs</span>
    <span style="font-size:11px;color:var(--text-muted)">|</span>
    <span style="font-size:11px;color:var(--text-secondary)">${phase.replace(/_/g,' ')}</span>
    <span style="flex:1"></span>
    <span id="map-freeze-badge" style="display:${wasFrozen?'flex':'none'};align-items:center;gap:6px;padding:3px 10px;background:rgba(255,180,50,0.15);border:1px solid rgba(255,180,50,0.3);border-radius:6px;font-size:10px;color:#ffb432;cursor:pointer" onclick="unfreezeMap()">
      <span style="font-size:10px">⏸</span> Paused <span style="font-size:9px;opacity:0.7">[click to resume]</span>
    </span>
    <span style="font-size:10px;color:var(--text-muted);font-family:'JetBrains Mono',monospace;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${thought}</span>`;
  }
  // Also update device table
  let rows = devs.map(d => '<tr onclick="showDeviceDetail(\\''+d.ip+'\\')" style="cursor:pointer"><td><code style="color:var(--accent)">'+d.ip+'</code></td><td>'+(d.hostname||'-')+'</td><td>'+(d.mac||'-')+'</td><td>'+(d.os_guess||'-')+'</td><td><span class="sev sev-'+(d.type==='router'?'high':'info')+'">'+(d.type||'?')+'</span></td><td>'+((d.services||[]).length)+'</td></tr>').join('');
  if(!rows) rows = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:24px">No devices discovered</td></tr>';
  const tbl = document.getElementById('map-table');
  if(tbl) tbl.innerHTML = '<div class="card"><div class="card-header">Device Inventory <span style="color:var(--text-muted);font-weight:400;font-size:12px">'+devs.length+' hosts</span></div><div class="card-body table-wrap"><table><thead><tr><th>IP</th><th>Hostname</th><th>MAC</th><th>OS</th><th>Type</th><th>Services</th></tr></thead><tbody>'+rows+'</tbody></table></div></div>';
}

setInterval(async()=>{
  if(currentPage!=='map') return;
  if(mapFrozen) return;
  await fetchMapData();
  updateMapStatusOnly();
}, 10000);
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def ui_home():
    return HTML_TEMPLATE