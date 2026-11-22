#!/usr/bin/env python3
"""Offboarding Checklist POC — single-file Flask app.

Interactive offboarding checklist with progress bar and audit log.
No external dependencies beyond Flask (pip-installed in the Docker image).
"""

import json
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DATA_FILE = "/data/offboarding_state.json"

CHECKLIST_CATEGORIES = [
    {
        "category": "Revoke System Access",
        "items": [
            "Disable email account",
            "Deactivate chat (Mattermost/Slack)",
            "Revoke file sharing access (Nextcloud)",
            "Remove CRM access",
            "Remove project management tool access",
            "Revoke code repository access (Gitea)",
            "Remove cloud console access",
        ],
    },
    {
        "category": "Recover Hardware",
        "items": [
            "Collect laptop",
            "Collect phone",
            "Collect keys and badges",
            "Collect any other company equipment",
        ],
    },
    {
        "category": "Transfer Data Ownership",
        "items": [
            "Reassign files and documents to manager",
            "Transfer project leads",
            "Reassign recurring meetings",
            "Update shared contact lists",
        ],
    },
    {
        "category": "Process Final Paperwork",
        "items": [
            "Process final paycheck",
            "Terminate benefits",
            "Send exit survey",
            "Update employee record in HR system",
        ],
    },
    {
        "category": "Archive Accounts",
        "items": [
            "Preserve emails for compliance",
            "Archive chat messages",
            "Disable (do not delete) accounts",
        ],
    },
    {
        "category": "Update Directories",
        "items": [
            "Remove from company directory",
            "Remove from mailing lists",
            "Update org chart",
        ],
    },
    {
        "category": "Notify Stakeholders",
        "items": [
            "Inform the team",
            "Inform clients and external partners",
            "Send farewell on behalf of the company",
        ],
    },
]


def _all_items():
    items = []
    for cat in CHECKLIST_CATEGORIES:
        for item in cat["items"]:
            items.append(item)
    return items


def _load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # Initialise: all unchecked, empty audit log
    return {"checked": {}, "audit_log": []}


def _save_state(state):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _add_audit(state, action, item):
    state["audit_log"].append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "action": action,
            "item": item,
        }
    )
    # Keep last 200 entries
    state["audit_log"] = state["audit_log"][-200:]


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offboarding Checklist — ARDOT Consulting POC</title>
<style>
  :root {
    --bg: #0f1117; --card: #1a1d27; --accent: #4f9cf9; --text: #e0e0e0;
    --muted: #888; --green: #4caf50; --border: #2a2d3a;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem 1rem; }
  .container { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 1.8rem; margin-bottom: 0.25rem; }
  .subtitle { color: var(--muted); margin-bottom: 1.5rem; font-size: 0.95rem; }
  .progress-bar { background: var(--border); border-radius: 8px; height: 24px;
                  margin-bottom: 1.5rem; overflow: hidden; position: relative; }
  .progress-fill { background: var(--green); height: 100%; border-radius: 8px;
                   transition: width 0.4s ease; display: flex; align-items: center;
                   justify-content: center; font-size: 0.8rem; font-weight: bold; color: #fff;
                   min-width: 0; }
  .progress-text { position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%);
                   font-size: 0.8rem; color: var(--text); }
  .category { background: var(--card); border: 1px solid var(--border); border-radius: 12px;
              margin-bottom: 1rem; overflow: hidden; }
  .category-header { padding: 0.8rem 1.2rem; font-weight: 600; font-size: 1.05rem;
                     border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; }
  .category-count { color: var(--muted); font-size: 0.85rem; font-weight: 400; }
  .item { padding: 0.6rem 1.2rem; border-bottom: 1px solid var(--border); cursor: pointer;
          display: flex; align-items: center; gap: 0.6rem; transition: background 0.15s; }
  .item:hover { background: rgba(255,255,255,0.03); }
  .item:last-child { border-bottom: none; }
  .checkbox { width: 20px; height: 20px; border: 2px solid var(--muted); border-radius: 4px;
              flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
  .item.checked .checkbox { background: var(--green); border-color: var(--green); }
  .item.checked .checkbox::after { content: '✓'; color: #fff; font-size: 14px; }
  .item.checked .item-label { text-decoration: line-through; color: var(--muted); }
  .audit-section { margin-top: 2rem; }
  .audit-section h2 { font-size: 1.2rem; margin-bottom: 0.75rem; }
  .audit-log { background: var(--card); border: 1px solid var(--border); border-radius: 12px;
               padding: 1rem 1.2rem; max-height: 300px; overflow-y: auto; font-size: 0.85rem; }
  .audit-entry { padding: 0.3rem 0; border-bottom: 1px solid var(--border); color: var(--muted); }
  .audit-entry:last-child { border-bottom: none; }
  .audit-entry .action { font-weight: 600; color: var(--text); }
  .audit-entry .ts { color: var(--accent); font-size: 0.8rem; }
  .reset-btn { margin-top: 1.5rem; padding: 0.5rem 1.2rem; background: var(--card);
               border: 1px solid var(--border); border-radius: 8px; color: var(--muted);
               cursor: pointer; font-size: 0.85rem; }
  .reset-btn:hover { border-color: #e53935; color: #e53935; }
  .footer { margin-top: 2rem; text-align: center; color: var(--muted); font-size: 0.8rem; }
  .footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>
<div class="container">
  <h1>Employee Offboarding Checklist</h1>
  <p class="subtitle">Interactive demo from
    <a href="https://www.ardotconsulting.com/2026/11/22/automating-employee-offboarding-with-open-source-tools/"
       style="color:var(--accent);text-decoration:none">Automating Employee Offboarding with Open Source Tools</a>
  </p>

  <div class="progress-bar">
    <div class="progress-fill" id="progress-fill" style="width:0%"></div>
    <span class="progress-text" id="progress-text">0 / 0 completed</span>
  </div>

  <div id="checklist"></div>

  <div class="audit-section">
    <h2>Audit Log</h2>
    <div class="audit-log" id="audit-log">
      <div class="audit-entry" style="text-align:center">No actions yet. Click items to start tracking.</div>
    </div>
  </div>

  <button class="reset-btn" onclick="resetAll()">Reset checklist</button>

  <div class="footer">
    <p>Proof of concept by <a href="https://www.ardotconsulting.com">ARDOT Consulting</a></p>
  </div>
</div>

<script>
const categories = {{ categories_json | safe }};
let checked = {{ checked_json | safe }};
const allItems = [];

categories.forEach(cat => {
  cat.items.forEach(item => allItems.push(item));
});

function toggleItem(item) {
  fetch('/api/toggle', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({item: item})
  })
  .then(r => r.json())
  .then(data => {
    checked = data.checked;
    render();
  });
}

function resetAll() {
  fetch('/api/reset', {method: 'POST'})
  .then(r => r.json())
  .then(data => {
    checked = {};
    render();
  });
}

function render() {
  // Progress
  const done = Object.values(checked).filter(v => v).length;
  const total = allItems.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-text').textContent = done + ' / ' + total + ' completed';

  // Checklist
  const container = document.getElementById('checklist');
  container.innerHTML = '';
  categories.forEach(cat => {
    const catDone = cat.items.filter(i => checked[i]).length;
    const div = document.createElement('div');
    div.className = 'category';
    div.innerHTML = '<div class="category-header">' + cat.category +
      '<span class="category-count">' + catDone + '/' + cat.items.length + '</span></div>';
    cat.items.forEach(item => {
      const itemDiv = document.createElement('div');
      itemDiv.className = 'item' + (checked[item] ? ' checked' : '');
      itemDiv.innerHTML = '<div class="checkbox"></div><span class="item-label">' + item + '</span>';
      itemDiv.onclick = () => toggleItem(item);
      div.appendChild(itemDiv);
    });
    container.appendChild(div);
  });

  // Audit log
  fetch('/api/audit').then(r => r.json()).then(data => {
    const logDiv = document.getElementById('audit-log');
    if (!data.entries || data.entries.length === 0) {
      logDiv.innerHTML = '<div class="audit-entry" style="text-align:center">No actions yet. Click items to start tracking.</div>';
    } else {
      logDiv.innerHTML = data.entries.slice().reverse().map(e =>
        '<div class="audit-entry"><span class="action">' + e.action + '</span> ' + e.item +
        ' <span class="ts">— ' + e.timestamp + '</span></div>'
      ).join('');
    }
  });
}

render();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    state = _load_state()
    return render_template_string(
        HTML_TEMPLATE,
        categories_json=json.dumps(CHECKLIST_CATEGORIES),
        checked_json=json.dumps(state.get("checked", {})),
    )


@app.route("/api/toggle", methods=["POST"])
def toggle():
    data = request.get_json()
    item = data.get("item", "")
    state = _load_state()
    current = state.get("checked", {}).get(item, False)
    state.setdefault("checked", {})[item] = not current
    action = "Checked" if not current else "Unchecked"
    _add_audit(state, action, item)
    _save_state(state)
    return jsonify({"checked": state["checked"]})


@app.route("/api/audit")
def audit():
    state = _load_state()
    return jsonify({"entries": state.get("audit_log", [])})


@app.route("/api/reset", methods=["POST"])
def reset():
    state = {"checked": {}, "audit_log": []}
    _save_state(state)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=port)
