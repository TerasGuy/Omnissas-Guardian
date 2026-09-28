"""Omnissa Guardian desktop window (pywebview) — dark console UI."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from omnissa_archive.guardian import GuardianApp
from omnissa_archive.guardian_i18n import STRINGS, normalize_lang, t

_ICON = Path(__file__).resolve().parents[2] / "assets" / "omnissa-guardian.ico"

DESKTOP_HTML = r"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>Omnissa Guardian Ultimate</title>
<style>
:root {
  --bg:#12141c; --panel:#1a1d27; --panel2:#222633; --line:#2e3344;
  --text:#e8eaef; --muted:#9aa3b5; --cyan:#4d889d; --coral:#f07a58;
  --gold:#e8b545; --ink:#2c2c3e; --green:#2ecc71; --red:#c0392b;
  --fatal:#c0392b; --error:#e74c3c; --warn:#e8b545; --debug:#3498db; --info:#95a5a6;
}
* { box-sizing:border-box; }
html, body { margin:0; height:100%; background:var(--bg); color:var(--text);
  font-family:"Segoe UI", Tahoma, Arial, sans-serif; }
body { display:flex; flex-direction:column; min-height:100vh; }
.header { display:flex; justify-content:space-between; align-items:center;
  padding:14px 18px 10px; border-bottom:1px solid var(--line); background:var(--panel); }
.brand-wrap { display:flex; gap:12px; align-items:center; }
.logo { width:34px; height:34px; border:2px solid var(--cyan); border-radius:8px;
  transform:rotate(45deg); position:relative; }
.logo:after { content:""; position:absolute; inset:5px; border:1px solid var(--coral);
  border-radius:4px; }
.brand { font-weight:800; letter-spacing:.04em; font-size:18px; }
.sub { color:var(--muted); font-size:12px; margin-top:2px; }
.header-actions { display:flex; gap:8px; align-items:center; }
.lang-btn, .ghost-btn {
  background:var(--panel2); color:var(--text); border:1px solid var(--line);
  border-radius:8px; padding:7px 12px; cursor:pointer; font-weight:700;
}
.lang-btn.active { border-color:var(--cyan); color:#fff; background:#24303a; }
.ver { color:var(--muted); font-size:12px; margin-inline-start:6px; }
.counters { display:flex; gap:8px; padding:10px 18px; align-items:center; flex-wrap:wrap; }
.counter { min-width:88px; text-align:center; padding:8px 10px; border-radius:6px; font-weight:800; color:#fff; }
.counter small { display:block; font-size:11px; opacity:.9; letter-spacing:.04em; }
.counter .n { font-size:20px; line-height:1.1; }
.c-fatal { background:var(--fatal); } .c-error { background:var(--error); }
.c-warn { background:var(--warn); color:#1b1b1b; } .c-debug { background:var(--debug); }
.c-info { background:var(--info); color:#1b1b1b; }
.det-note { margin-inline-start:auto; color:var(--muted); font-size:13px; }
.status-bar { margin:0 18px 8px; padding:10px 14px; border-radius:6px;
  display:flex; justify-content:space-between; align-items:center; gap:12px;
  background:#5a1f1f; border:1px solid #7a2b2b; }
.status-bar.run { background:#1e3d2f; border-color:#2f6b4a; }
.status-bar .dot { width:10px; height:10px; border-radius:50%; background:#e74c3c;
  display:inline-block; margin-inline-end:8px; }
.status-bar.run .dot { background:var(--green); }
.start-btn { background:var(--green); color:#083018; border:0; border-radius:6px;
  padding:10px 16px; font-weight:800; cursor:pointer; letter-spacing:.02em; }
.start-btn.stop { background:var(--coral); color:#fff; }
.tabs { display:flex; gap:2px; padding:0 18px; border-bottom:1px solid var(--line);
  overflow:auto; background:var(--panel); }
.tab { background:transparent; border:0; color:var(--muted); padding:12px 14px;
  cursor:pointer; font-weight:700; border-bottom:2px solid transparent; white-space:nowrap; }
.tab.active { color:var(--cyan); border-bottom-color:var(--cyan); }
.main { flex:1; padding:14px 18px 10px; overflow:auto; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }
.toolbar { display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-bottom:10px; }
.toolbar h2 { margin:0; font-size:15px; }
.filters { display:flex; gap:10px; flex-wrap:wrap; align-items:center; color:var(--muted); font-size:13px; }
.filters label { display:inline-flex; gap:5px; align-items:center; cursor:pointer; }
.swatch { width:10px; height:10px; border-radius:2px; display:inline-block; }
.actions { margin-inline-start:auto; display:flex; gap:8px; }
.btn { background:var(--panel2); color:var(--text); border:1px solid var(--line);
  border-radius:6px; padding:8px 12px; cursor:pointer; font-weight:700; }
.btn.purple { background:#5b3d8f; border-color:#6d4aa8; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:6px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:start; background:var(--panel2); color:var(--muted); padding:10px;
  border-bottom:1px solid var(--line); position:sticky; top:0; }
td { padding:10px; border-bottom:1px solid var(--line); vertical-align:top; }
tr:hover td { background:#1f2330; cursor:pointer; }
.level { font-weight:800; }
.level.FATAL { color:#ff6b6b; } .level.ERROR { color:#ff8e7a; }
.level.WARNING { color:var(--gold); } .level.DEBUG { color:#7ec8ff; }
.level.INFO { color:#c0c6d0; }
.hint { color:var(--muted); font-size:12px; margin-top:10px; }
.path-row { display:grid; grid-template-columns:28px 1fr auto; gap:10px; align-items:start;
  padding:10px 0; border-bottom:1px solid var(--line); }
.path-row code { display:block; color:var(--cyan); font-size:12px; margin-top:3px; direction:ltr; text-align:left; }
input[type=text], input[type=number] {
  width:100%; padding:9px 10px; border-radius:6px; border:1px solid var(--line);
  background:var(--panel2); color:var(--text); font:inherit;
}
.grid { display:grid; gap:10px; grid-template-columns:1fr 1fr; }
.modal { position:fixed; inset:0; background:rgba(0,0,0,.55); display:none;
  align-items:center; justify-content:center; z-index:20; padding:20px; }
.modal.open { display:flex; }
.modal .box { width:min(720px,100%); max-height:85vh; overflow:auto; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; padding:16px; }
.modal pre { white-space:pre-wrap; background:var(--panel2); padding:10px; border-radius:6px;
  direction:ltr; text-align:left; font-size:12px; }
.kb-item { border:1px solid var(--line); border-radius:8px; padding:10px; margin:8px 0; }
.kb-item a { color:var(--coral); font-weight:700; }
.sys-line { font-family:Consolas,monospace; font-size:12px; padding:4px 0;
  border-bottom:1px solid var(--line); direction:ltr; text-align:left; }
.hidden { display:none !important; }
@media (max-width:900px){ .grid{grid-template-columns:1fr;} }
</style>
</head>
<body>
  <div class="header">
    <div class="brand-wrap">
      <div class="logo"></div>
      <div>
        <div class="brand" id="brand"></div>
        <div class="sub" id="subtitle"></div>
      </div>
    </div>
    <div class="header-actions">
      <button class="lang-btn" id="btn-he" type="button">עברית</button>
      <button class="lang-btn" id="btn-en" type="button">English</button>
      <span class="ver" id="version"></span>
    </div>
  </div>

  <div class="counters">
    <div class="counter c-fatal"><small id="lbl-fatal">FATAL</small><div class="n" id="n-fatal">0</div></div>
    <div class="counter c-error"><small id="lbl-error">ERROR</small><div class="n" id="n-error">0</div></div>
    <div class="counter c-warn"><small id="lbl-warning">WARNING</small><div class="n" id="n-warn">0</div></div>
    <div class="counter c-debug"><small id="lbl-debug">DEBUG</small><div class="n" id="n-debug">0</div></div>
    <div class="counter c-info"><small id="lbl-info">INFO</small><div class="n" id="n-info">0</div></div>
    <div class="det-note" id="det-note"></div>
  </div>

  <div class="status-bar" id="status-bar">
    <div><span class="dot"></span><span id="status-text"></span></div>
    <button class="start-btn" id="monitor-btn" type="button"></button>
  </div>

  <div class="tabs" id="tabs"></div>
  <div class="main">
    <section class="panel tabpane" id="pane-live">
      <div class="toolbar">
        <h2 id="realtime"></h2>
        <div class="filters" id="filters"></div>
        <div class="actions">
          <button class="btn" id="btn-clear" type="button"></button>
          <button class="btn purple" id="btn-search" type="button"></button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th id="th-ts"></th><th id="th-level"></th><th id="th-file"></th>
            <th id="th-msg"></th><th id="th-sug"></th><th id="th-kb"></th>
          </tr></thead>
          <tbody id="live-body"></tbody>
        </table>
      </div>
      <div class="hint" id="detail-hint"></div>
    </section>

    <section class="panel tabpane hidden" id="pane-history">
      <h2 id="history-title"></h2>
      <div class="table-wrap" style="margin-top:10px">
        <table>
          <thead><tr>
            <th id="th2-ts"></th><th id="th2-level"></th><th id="th2-file"></th>
            <th id="th2-msg"></th><th id="th2-sug"></th><th id="th2-kb"></th>
          </tr></thead>
          <tbody id="history-body"></tbody>
        </table>
      </div>
      <div class="hint" id="history-empty"></div>
    </section>

    <section class="panel tabpane hidden" id="pane-watch">
      <h2 id="watch-title"></h2>
      <p class="hint" id="watch-help"></p>
      <div id="targets"></div>
      <div class="grid" style="margin-top:12px">
        <label><span id="lbl-interval"></span><input type="number" id="interval" min="15" step="15"></label>
        <label><span id="lbl-extra"></span><input type="text" id="extra" placeholder="\\server\share\logs"></label>
      </div>
      <div class="actions" style="margin:12px 0 0; justify-content:flex-start">
        <button class="btn purple" id="btn-save" type="button"></button>
        <button class="btn" id="btn-scan" type="button"></button>
      </div>
    </section>

    <section class="panel tabpane hidden" id="pane-kb">
      <h2 id="kb-title"></h2>
      <p><span id="lbl-db"></span>: <code id="db-path" style="direction:ltr"></code></p>
      <div class="actions" style="margin:10px 0; justify-content:flex-start">
        <button class="btn purple" id="btn-open-reader" type="button"></button>
      </div>
      <input type="text" id="kb-query" style="margin-top:8px">
      <div id="kb-results" style="margin-top:10px"></div>
      <h3 id="online-title" style="margin-top:18px"></h3>
      <p class="hint" id="online-help"></p>
      <div id="online-sources"></div>
      <button class="btn" id="btn-online" type="button" style="margin-top:10px"></button>
      <p class="hint" id="online-status"></p>
    </section>

    <section class="panel tabpane hidden" id="pane-settings">
      <h2 id="settings-title"></h2>
      <div class="grid" style="margin-top:12px">
        <label><span id="lbl-settings-lang"></span>
          <select id="settings-lang" style="width:100%;padding:9px;border-radius:6px;background:#222633;color:#fff;border:1px solid #2e3344">
            <option value="he">עברית</option>
            <option value="en">English</option>
          </select>
        </label>
        <label><span id="lbl-settings-interval"></span><input type="number" id="settings-interval" min="15" step="15"></label>
        <label style="grid-column:1/-1"><span id="lbl-settings-reader"></span><input type="text" id="settings-reader"></label>
        <label style="grid-column:1/-1;display:flex;gap:8px;align-items:center">
          <input type="checkbox" id="settings-online" style="width:auto">
          <span id="lbl-settings-online"></span>
        </label>
      </div>
      <p class="hint" id="online-settings-hint"></p>
      <button class="btn purple" id="btn-settings-save" type="button" style="margin-top:12px"></button>
    </section>

    <section class="panel tabpane hidden" id="pane-email">
      <h2 id="email-title"></h2>
      <p class="hint" id="email-stub"></p>
    </section>

    <section class="panel tabpane hidden" id="pane-system">
      <h2 id="system-title"></h2>
      <div id="system-log" style="margin-top:10px"></div>
      <div class="hint" id="system-empty"></div>
    </section>
  </div>

  <div class="modal" id="modal">
    <div class="box">
      <h2 id="detail-title"></h2>
      <p><strong id="built-in-lbl"></strong></p>
      <pre id="detail-builtin"></pre>
      <p><strong id="kb-matches-lbl"></strong></p>
      <div id="detail-kb"></div>
      <button class="btn" id="btn-detail-online" type="button" style="margin-top:10px"></button>
      <p class="hint" id="detail-online-status"></p>
      <button class="btn" id="btn-close" type="button" style="margin-top:10px"></button>
    </div>
  </div>

<script>
const LEVELS = ["FATAL","ERROR","WARNING","DEBUG","INFO"];
const state = { lang:"he", strings:{}, snap:null, filters:new Set(LEVELS), tab:"live", alerts:{} };
const $ = (id) => document.getElementById(id);
const brand = $("brand"), subtitle = $("subtitle"), version = $("version");
const btnHe = $("btn-he"), btnEn = $("btn-en");
const nFatal = $("n-fatal"), nError = $("n-error"), nWarn = $("n-warn");
const nDebug = $("n-debug"), nInfo = $("n-info"), detNote = $("det-note");
const statusBar = $("status-bar"), statusText = $("status-text"), monitorBtn = $("monitor-btn");
const tabs = $("tabs"), filters = $("filters");
const realtime = $("realtime"), btnClear = $("btn-clear"), btnSearch = $("btn-search");
const thTs = $("th-ts"), thLevel = $("th-level"), thFile = $("th-file");
const thMsg = $("th-msg"), thSug = $("th-sug"), thKb = $("th-kb");
const th2Ts = $("th2-ts"), th2Level = $("th2-level"), th2File = $("th2-file");
const th2Msg = $("th2-msg"), th2Sug = $("th2-sug"), th2Kb = $("th2-kb");
const detailHint = $("detail-hint"), liveBody = $("live-body");
const historyTitle = $("history-title"), historyBody = $("history-body"), historyEmpty = $("history-empty");
const watchTitle = $("watch-title"), watchHelp = $("watch-help"), targets = $("targets");
const lblInterval = $("lbl-interval"), lblExtra = $("lbl-extra");
const interval = $("interval"), extra = $("extra");
const btnSave = $("btn-save"), btnScan = $("btn-scan");
const kbTitle = $("kb-title"), lblDb = $("lbl-db"), dbPath = $("db-path");
const btnOpenReader = $("btn-open-reader"), kbQuery = $("kb-query"), kbResults = $("kb-results");
const onlineTitle = $("online-title"), onlineHelp = $("online-help");
const onlineSources = $("online-sources"), btnOnline = $("btn-online"), onlineStatus = $("online-status");
const settingsTitle = $("settings-title"), lblSettingsLang = $("lbl-settings-lang");
const lblSettingsInterval = $("lbl-settings-interval"), lblSettingsReader = $("lbl-settings-reader");
const lblSettingsOnline = $("lbl-settings-online"), onlineSettingsHint = $("online-settings-hint");
const settingsLang = $("settings-lang"), settingsInterval = $("settings-interval");
const settingsReader = $("settings-reader"), settingsOnline = $("settings-online");
const btnSettingsSave = $("btn-settings-save");
const emailTitle = $("email-title"), emailStub = $("email-stub");
const systemTitle = $("system-title"), systemLog = $("system-log"), systemEmpty = $("system-empty");
const modal = $("modal"), detailTitle = $("detail-title"), builtInLbl = $("built-in-lbl");
const kbMatchesLbl = $("kb-matches-lbl"), detailBuiltin = $("detail-builtin");
const detailKb = $("detail-kb"), btnDetailOnline = $("btn-detail-online");
const detailOnlineStatus = $("detail-online-status"), btnClose = $("btn-close");
let detailLine = "";

function S(key, vars) {
  let s = (state.strings[state.lang] || {})[key] || key;
  if (vars) Object.keys(vars).forEach(k => { s = s.replace("{"+k+"}", vars[k]); });
  return s;
}

function applyI18n() {
  const rtl = state.lang === "he";
  document.documentElement.lang = state.lang;
  document.documentElement.dir = rtl ? "rtl" : "ltr";
  document.title = S("app_title");
  brand.textContent = S("brand");
  subtitle.textContent = S("subtitle");
  version.textContent = S("version");
  btnHe.classList.toggle("active", state.lang==="he");
  btnEn.classList.toggle("active", state.lang==="en");
  ["fatal","error","warning","debug","info"].forEach(k => {
    document.getElementById("lbl-"+k).textContent = S(k);
  });
  realtime.textContent = S("realtime");
  btnClear.textContent = "✕ " + S("clear");
  btnSearch.textContent = "🔍 " + S("search_kb");
  thTs.textContent = S("col_timestamp"); thLevel.textContent = S("col_level");
  thFile.textContent = S("col_logfile"); thMsg.textContent = S("col_message");
  thSug.textContent = S("col_suggestion"); thKb.textContent = S("col_kb");
  th2Ts.textContent = S("col_timestamp"); th2Level.textContent = S("col_level");
  th2File.textContent = S("col_logfile"); th2Msg.textContent = S("col_message");
  th2Sug.textContent = S("col_suggestion"); th2Kb.textContent = S("col_kb");
  detailHint.textContent = S("detail_hint");
  historyTitle.textContent = S("history_title");
  historyEmpty.textContent = S("history_empty");
  watchTitle.textContent = S("watch_title");
  watchHelp.textContent = S("watch_help");
  lblInterval.textContent = S("interval");
  lblExtra.textContent = S("extra_path");
  btnSave.textContent = S("save");
  btnScan.textContent = S("scan_now");
  kbTitle.textContent = S("kb_title");
  lblDb.textContent = S("kb_db");
  btnOpenReader.textContent = S("kb_open_reader");
  kbQuery.placeholder = S("kb_search_placeholder");
  onlineTitle.textContent = S("online_title");
  onlineHelp.textContent = S("online_help");
  btnOnline.textContent = S("online_search_btn");
  settingsTitle.textContent = S("settings_title");
  lblSettingsLang.textContent = S("settings_lang");
  lblSettingsInterval.textContent = S("settings_interval");
  lblSettingsReader.textContent = S("settings_reader");
  lblSettingsOnline.textContent = S("settings_online");
  onlineSettingsHint.textContent = S("settings_online_hint");
  btnSettingsSave.textContent = S("save");
  btnDetailOnline.textContent = S("online_search_btn");
  emailTitle.textContent = S("email_title");
  emailStub.textContent = S("email_stub");
  systemTitle.textContent = S("system_title");
  systemEmpty.textContent = S("system_empty");
  detailTitle.textContent = S("detail_title");
  builtInLbl.textContent = S("built_in");
  kbMatchesLbl.textContent = S("kb_matches");
  btnClose.textContent = S("close");
  renderTabs();
  renderFilters();
  renderStatus();
}

function renderTabs() {
  const defs = [
    ["live","tab_live"],["history","tab_history"],["watch","tab_watch"],
    ["kb","tab_kb"],["settings","tab_settings"],["email","tab_email"],["system","tab_system"]
  ];
  tabs.innerHTML = "";
  defs.forEach(([id, key]) => {
    const b = document.createElement("button");
    b.className = "tab" + (state.tab===id ? " active" : "");
    b.type = "button";
    b.textContent = S(key);
    b.onclick = () => { state.tab = id; showTab(); };
    tabs.appendChild(b);
  });
}

function showTab() {
  document.querySelectorAll(".tabpane").forEach(el => el.classList.add("hidden"));
  document.getElementById("pane-"+state.tab).classList.remove("hidden");
  renderTabs();
  if (state.tab === "history") renderHistory();
  if (state.tab === "watch") renderTargets();
  if (state.tab === "system") renderSystem();
  if (state.tab === "kb") renderOnlineSources();
  if (state.tab === "settings" && state.snap) {
    settingsLang.value = state.snap.language;
    settingsInterval.value = state.snap.interval_seconds;
    settingsReader.value = state.snap.reader_base;
    settingsOnline.checked = !!state.snap.online_search;
  }
}

function renderOnlineSources() {
  const sources = (state.snap && state.snap.online_sources) || [];
  onlineSources.innerHTML = sources.map(s => `
    <div class="path-row">
      <div></div>
      <div><strong>${esc(s.name||"")}</strong><code>${esc(s.url||"")}</code></div>
      <span></span>
    </div>`).join("");
}

function onlineMessage(result) {
  const status = (result && result.status) || "disabled";
  if (status === "offline") return S("online_offline");
  if (status === "empty") return S("online_empty");
  if (status === "ok") return S("online_opened", {n: (result.urls||[]).length});
  return S("online_disabled");
}

async function runOnlineSearch(query, statusEl) {
  const result = await window.pywebview.api.search_online(query || "");
  statusEl.textContent = onlineMessage(result);
}

function renderFilters() {
  filters.innerHTML = `<span>${S("filter")}</span>`;
  const colors = {FATAL:"#c0392b",ERROR:"#e74c3c",WARNING:"#e8b545",DEBUG:"#3498db",INFO:"#95a5a6"};
  LEVELS.forEach(level => {
    const lab = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = state.filters.has(level);
    cb.onchange = () => {
      if (cb.checked) state.filters.add(level); else state.filters.delete(level);
      renderLive();
    };
    lab.appendChild(cb);
    const sw = document.createElement("span");
    sw.className = "swatch";
    sw.style.background = colors[level];
    lab.appendChild(sw);
    lab.appendChild(document.createTextNode(" " + S(level.toLowerCase())));
    filters.appendChild(lab);
  });
}

function statusLabel(code) {
  return ({ok:S("path_ok"), missing:S("path_missing"), unc:S("path_unc"),
           pattern:S("path_pattern"), empty:S("path_empty")})[code] || code;
}

function renderStatus() {
  if (!state.snap) return;
  const running = !!state.snap.running;
  statusBar.classList.toggle("run", running);
  statusText.textContent = running
    ? S("status_running", {sec: state.snap.interval_seconds})
    : S("status_stopped");
  monitorBtn.textContent = (running ? "⏹ " : "▶ ") + (running ? S("stop_monitoring") : S("start_monitoring"));
  monitorBtn.classList.toggle("stop", running);
  const c = state.snap.counts || {};
  nFatal.textContent = c.FATAL || 0;
  nError.textContent = c.ERROR || 0;
  nWarn.textContent = c.WARNING || 0;
  nDebug.textContent = c.DEBUG || 0;
  nInfo.textContent = c.INFO || 0;
  const total = Object.values(c).reduce((a,b)=>a+b,0);
  detNote.textContent = total ? S("detections_count", {n: total}) : S("no_detections");
  dbPath.textContent = state.snap.database || "";
  interval.value = state.snap.interval_seconds || 60;
}

function rowHtml(a) {
  return `<tr data-id="${a.id}">
    <td>${esc(a.at||"")}</td>
    <td class="level ${esc(a.level||"")}">${esc(a.level||"")}</td>
    <td>${esc(a.logfile || a.path || "")}</td>
    <td>${esc(a.line||"")}</td>
    <td>${esc((a.suggestion||"").slice(0,120))}</td>
    <td>${esc(a.kb||"")}</td>
  </tr>`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
}

function renderLive() {
  const alerts = (state.snap && state.snap.alerts) || [];
  state.alerts = {};
  alerts.forEach(a => { state.alerts[a.id] = a; });
  const rows = alerts.filter(a => state.filters.has(a.level || "ERROR"));
  liveBody.innerHTML = rows.map(rowHtml).join("");
  liveBody.querySelectorAll("tr").forEach(tr => {
    tr.ondblclick = () => openDetail(state.alerts[tr.dataset.id]);
  });
}

function renderHistory() {
  const rows = (state.snap && state.snap.history) || [];
  historyBody.innerHTML = rows.map(rowHtml).join("");
  historyEmpty.style.display = rows.length ? "none" : "block";
  historyBody.querySelectorAll("tr").forEach(tr => {
    const id = tr.dataset.id;
    const item = rows.find(r => String(r.id) === String(id));
    tr.ondblclick = () => openDetail(item);
  });
}

function renderTargets() {
  if (!state.snap) return;
  const pathStatusKey = {ok:"path_ok", missing:"path_missing", unc:"path_unc", pattern:"path_pattern", empty:"path_empty"};
  targets.innerHTML = (state.snap.targets || []).map(t => `
    <div class="path-row">
      <input type="checkbox" data-id="${esc(t.id)}" ${t.enabled ? "checked" : ""}>
      <div><strong>${esc(t.label)}</strong><code>${esc(t.path)}</code></div>
      <span>${statusLabel(t.status)}</span>
    </div>`).join("") + (state.snap.extra_paths||[]).map(e => `
    <div class="path-row">
      <input type="checkbox" checked disabled>
      <div><strong>${S("extra_path")}</strong><code>${esc(e.path)}</code></div>
      <span>${statusLabel(e.status)}</span>
    </div>`).join("");
}

function renderSystem() {
  const rows = (state.snap && state.snap.system_log) || [];
  systemLog.innerHTML = rows.map(r => `<div class="sys-line">${esc(r.at)}  ${esc(r.message)}</div>`).join("");
  systemEmpty.style.display = rows.length ? "none" : "block";
}

function openDetail(alert) {
  if (!alert) return;
  detailLine = alert.line || "";
  detailOnlineStatus.textContent = "";
  detailBuiltin.textContent = alert.suggestion || "";
  const items = alert.suggestions || [];
  detailKb.innerHTML = items.length ? items.map(s => `
    <div class="kb-item">
      <div><strong>${esc(s.title)}</strong></div>
      <div class="hint">${esc(s.published_at || "")} · ${esc((s.excerpt||"").slice(0,180))}</div>
      <a href="#" data-link="${esc(s.reader_link||"")}">${S("open_archive")}</a>
    </div>`).join("") : `<p class="hint">${S("no_match")}<br>${S("no_match_hint")}</p>`;
  detailKb.querySelectorAll("a").forEach(a => {
    a.onclick = (ev) => { ev.preventDefault(); window.pywebview.api.open_url(a.dataset.link); };
  });
  modal.classList.add("open");
}

async function refresh() {
  const snap = await window.pywebview.api.get_snapshot();
  state.snap = snap;
  state.lang = snap.language || state.lang;
  applyI18n();
  renderLive();
  if (state.tab === "history") renderHistory();
  if (state.tab === "watch") renderTargets();
  if (state.tab === "kb") renderOnlineSources();
  if (state.tab === "system") renderSystem();
}

window.addEventListener("pywebviewready", async () => {
  state.strings = await window.pywebview.api.get_strings();
  await refresh();
  setInterval(refresh, 2000);
});

btnHe.onclick = async () => { await window.pywebview.api.set_language("he"); await refresh(); };
btnEn.onclick = async () => { await window.pywebview.api.set_language("en"); await refresh(); };
monitorBtn.onclick = async () => {
  const running = !!(state.snap && state.snap.running);
  await window.pywebview.api.set_monitoring(!running);
  await refresh();
};
btnClear.onclick = async () => { await window.pywebview.api.clear_alerts(); await refresh(); };
btnSearch.onclick = () => { state.tab = "kb"; showTab(); kbQuery.focus(); };
btnSave.onclick = async () => {
  const ids = [...targets.querySelectorAll("input[type=checkbox][data-id]:checked")].map(el => el.dataset.id);
  await window.pywebview.api.save_watch(ids, Number(interval.value||60), extra.value||"");
  extra.value = "";
  await refresh();
};
btnScan.onclick = async () => { await window.pywebview.api.scan_now(); await refresh(); };
btnOpenReader.onclick = async () => { await window.pywebview.api.open_reader(); };
btnSettingsSave.onclick = async () => {
  await window.pywebview.api.set_language(settingsLang.value);
  await window.pywebview.api.save_settings(
    Number(settingsInterval.value||60),
    settingsReader.value||"",
    !!settingsOnline.checked
  );
  await refresh();
};
btnOnline.onclick = () => runOnlineSearch(kbQuery.value || "", onlineStatus);
btnDetailOnline.onclick = () => runOnlineSearch(detailLine, detailOnlineStatus);
btnClose.onclick = () => modal.classList.remove("open");
kbQuery.addEventListener("keydown", async (ev) => {
  if (ev.key !== "Enter") return;
  const rows = await window.pywebview.api.search_kb(kbQuery.value || "");
  kbResults.innerHTML = (rows||[]).map(s => `
    <div class="kb-item"><strong>${esc(s.title)}</strong>
    <div class="hint">${esc((s.excerpt||"").slice(0,200))}</div>
    <a href="#" data-link="${esc(s.reader_link||"")}">${S("open_archive")}</a></div>`).join("")
    || `<p class="hint">${S("no_match")}</p>`;
  kbResults.querySelectorAll("a").forEach(a => {
    a.onclick = (e) => { e.preventDefault(); window.pywebview.api.open_url(a.dataset.link); };
  });
});
</script>
</body>
</html>
"""


class GuardianApi:
    def __init__(self, app: GuardianApp) -> None:
        self.app = app

    def get_strings(self) -> dict:
        return STRINGS

    def get_snapshot(self) -> dict:
        return self.app.snapshot()

    def set_language(self, lang: str) -> str:
        return self.app.set_language(normalize_lang(lang))

    def set_monitoring(self, enabled: bool) -> bool:
        self.app.set_monitoring(bool(enabled))
        return bool(self.app.state.get("running"))

    def clear_alerts(self) -> str:
        self.app.clear_alerts()
        return t(self.app.language(), "cleared")

    def save_watch(self, enabled_ids: list, interval: int, extra: str = "") -> str:
        notice = self.app.update_watch_dirs(
            enabled_ids=list(enabled_ids or []),
            interval=int(interval or 60),
            extra=extra or "",
        )
        key = "extra_added" if notice == "extra_added" else "saved"
        return t(self.app.language(), key)

    def save_settings(self, interval: int, reader_base: str = "", online_search: bool = False) -> str:
        enabled = [item["id"] for item in self.app.state["targets"] if item.get("enabled")]
        self.app.set_online_search(bool(online_search))
        self.app.update_watch_dirs(
            enabled_ids=enabled,
            interval=int(interval or 60),
            reader_base=reader_base or None,
        )
        return t(self.app.language(), "saved")

    def search_online(self, query: str) -> dict:
        result = self.app.prepare_online_search(query or "")
        if result.get("status") == "ok":
            for item in result.get("urls") or []:
                url = item.get("url") or ""
                if url:
                    webbrowser.open(url)
        return result

    def scan_now(self) -> str:
        count = self.app.scan_once()
        return t(self.app.language(), "scan_done", n=count)

    def search_kb(self, query: str) -> list:
        return self.app.search_archive(query or "")

    def open_reader(self) -> None:
        webbrowser.open(self.app.reader_base + "/")

    def open_url(self, url: str) -> None:
        if url:
            webbrowser.open(url)


def run_desktop(
    data_dir: Path,
    *,
    reader_base: str = "http://127.0.0.1:8765",
) -> None:
    import webview
    from urllib.parse import urlparse

    from omnissa_archive.reader import start_archive_server

    parsed = urlparse(reader_base)
    try:
        start_archive_server(data_dir, port=parsed.port or 8765)
    except OSError as exc:
        print(f"reader already running: {exc}", flush=True)

    app = GuardianApp(data_dir, reader_base=reader_base)
    app.start_worker()
    api = GuardianApi(app)
    window = webview.create_window(
        t(app.language(), "app_title") + " " + t(app.language(), "version"),
        html=DESKTOP_HTML,
        js_api=api,
        width=1280,
        height=820,
        min_size=(960, 640),
        background_color="#12141c",
    )

    def on_closed() -> None:
        app.stop()

    try:
        window.events.closed += on_closed
    except Exception:
        pass
    print("guardian-desktop ready", flush=True)
    webview.start(debug=False, icon=str(_ICON) if _ICON.is_file() else None)
    app.stop()
