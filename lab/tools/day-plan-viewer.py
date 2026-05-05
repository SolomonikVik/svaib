#!/usr/bin/env python3
"""Day Plan Viewer — показывает план дня из 03_plan.md в Safari.

Запуск: python3 lab/tools/day-plan-viewer.py
Остановка: Ctrl+C
"""

import http.server
import json
import os
import re
import webbrowser
from pathlib import Path

PORT = 8034
PLAN_FILE = Path(__file__).resolve().parent.parent.parent / "meta" / "management" / "03_plan.md"

# ─── Parser ───

def parse_plan():
    """Парсит секцию 'План дня' из 03_plan.md."""
    text = PLAN_FILE.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Найти начало секции "План дня"
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^## План дня", line):
            start = i
            break
    if start is None:
        return {"date": "?", "groups": []}

    # Извлечь дату из заголовка: ## План дня (среда, 18.03)
    date_match = re.search(r"\((.+?)\)", lines[start])
    date_str = date_match.group(1) if date_match else ""

    # Собрать задачи до следующего ## или конца файла
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^## ", lines[i]):
            end = i
            break

    groups = []
    current_group = None

    for i in range(start + 1, end):
        line = lines[i]

        # Заголовок группы ### Сделано / ### Делаем
        h3 = re.match(r"^### (.+)", line)
        if h3:
            current_group = {"title": h3.group(1).strip(), "tasks": []}
            groups.append(current_group)
            continue

        # Задача - [ ] или - [x]
        task_match = re.match(r"^(\s*)- \[([ x])\] (.+)", line)
        if task_match and current_group is not None:
            indent = len(task_match.group(1))
            current_group["tasks"].append({
                "line": i,
                "done": task_match.group(2) == "x",
                "text": task_match.group(3).strip(),
                "indent": indent,
            })

    return {"date": date_str, "groups": groups}


def toggle_task(line_num):
    """Переключает чекбокс на указанной строке."""
    text = PLAN_FILE.read_text(encoding="utf-8")
    lines = text.split("\n")

    if line_num < 0 or line_num >= len(lines):
        return False

    line = lines[line_num]
    if "- [ ] " in line:
        lines[line_num] = line.replace("- [ ] ", "- [x] ", 1)
    elif "- [x] " in line:
        lines[line_num] = line.replace("- [x] ", "- [ ] ", 1)
    else:
        return False

    PLAN_FILE.write_text("\n".join(lines), encoding="utf-8")
    return True


# ─── HTML ───

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>План дня</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&amp;family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@500;600&amp;display=swap" rel="stylesheet">
<style>
:root {
  --bg: #071015;
  --soft: #0B161B;
  --surface: #101D23;
  --surface-2: #13262D;
  --border: #25444D;
  --border-soft: rgba(0, 180, 166, 0.24);
  --text: #F0F8F7;
  --muted: #A7BABD;
  --soft-text: #789096;
  --accent: #00B4A6;
  --pink: #FF4D8D;
  --yellow: #FFD600;
  --done-text: #789096;
  --radius: 8px;
  --shadow: 0 22px 80px rgba(0, 0, 0, 0.28);
  --font-ui: "Inter", "Roboto", "Segoe UI", sans-serif;
  --font-display: "Sora", "Inter", sans-serif;
  --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-ui);
  color: var(--text);
  background:
    linear-gradient(180deg, rgba(0, 180, 166, 0.07) 0%, rgba(7, 16, 21, 0) 300px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.026) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.018) 1px, transparent 1px),
    var(--bg);
  background-size: auto, 72px 72px, 72px 72px, auto;
  border-top: 3px solid var(--accent);
  min-height: 100vh;
  padding: 36px 20px 48px;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.container {
  max-width: 680px;
  margin: 0 auto;
}

.header {
  font-family: var(--font-display);
  margin-bottom: 28px;
  padding: 26px 28px;
  background: linear-gradient(180deg, rgba(19, 38, 45, 0.92), rgba(11, 22, 27, 0.9));
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.header h1 {
  font-size: clamp(34px, 7vw, 48px);
  line-height: 1.04;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 8px;
}

.header .date {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.group {
  margin-bottom: 28px;
}

.group-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
  margin-bottom: 12px;
  padding-left: 4px;
}

.group-title.doing {
  color: var(--pink);
}

.group-title.meetings {
  color: var(--yellow);
}

.group-title.done-group {
  color: var(--accent);
}

.task {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  background: linear-gradient(180deg, rgba(19, 38, 45, 0.96), rgba(16, 29, 35, 0.96));
  border: 1px solid rgba(37, 68, 77, 0.9);
  border-radius: var(--radius);
  margin-bottom: 10px;
  cursor: pointer;
  transition: transform 0.12s, box-shadow 0.12s, border-color 0.12s, background 0.12s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.task:active {
  transform: scale(0.98);
}

.task:hover {
  border-color: rgba(0, 180, 166, 0.42);
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.22);
}

.task.done {
  background: rgba(11, 22, 27, 0.66);
  border-color: rgba(37, 68, 77, 0.62);
}

.task.done .task-text {
  text-decoration: line-through;
  color: var(--done-text);
}

.task.sub {
  margin-left: 28px;
}

.checkbox {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 2px solid rgba(0, 180, 166, 0.34);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  transition: background 0.15s, border-color 0.15s;
  background: rgba(7, 16, 21, 0.78);
}

.task.done .checkbox {
  background: var(--accent);
  border-color: var(--accent);
}

.checkmark {
  display: none;
  color: white;
  font-size: 14px;
  font-weight: 700;
}

.task.done .checkmark {
  display: block;
}

.task-text {
  font-size: 16px;
  line-height: 1.55;
  padding-top: 1px;
  color: var(--text);
}

.task-text strong {
  color: var(--text);
  font-weight: 800;
}

.task:not(.done) .task-text strong {
  color: #ffffff;
}

.task-text code {
  font-family: var(--font-mono);
  font-size: 0.86em;
  color: var(--accent);
  background: rgba(0, 180, 166, 0.1);
  border: 1px solid rgba(0, 180, 166, 0.18);
  border-radius: 4px;
  padding: 1px 5px;
}

.task-text a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid rgba(0, 180, 166, 0.42);
}

.status {
  text-align: center;
  font-size: 12px;
  color: var(--muted);
  margin-top: 34px;
  opacity: 0.68;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--muted);
  background: rgba(16, 29, 35, 0.72);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

@media (max-width: 640px) {
  body {
    padding: 18px 12px 34px;
    background-size: auto, 54px 54px, 54px 54px, auto;
  }

  .header {
    padding: 22px;
  }

  .task {
    padding: 15px 14px;
  }

  .task.sub {
    margin-left: 18px;
  }
}
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>План дня</h1>
    <div class="date" id="date"></div>
  </div>
  <div id="content"><div class="loading">Загрузка...</div></div>
  <div class="status" id="status"></div>
</div>

<script>
let refreshTimer;

async function loadPlan() {
  try {
    const res = await fetch('/api/plan');
    const data = await res.json();
    render(data);
  } catch (e) {
    document.getElementById('content').innerHTML =
      '<div class="loading">Ошибка загрузки</div>';
  }
}

function render(data) {
  document.getElementById('date').textContent = data.date;

  if (!data.groups.length) {
    document.getElementById('content').innerHTML =
      '<div class="loading">Секция «План дня» не найдена</div>';
    return;
  }

  let html = '';
  for (const group of data.groups) {
    html += `<div class="group">`;
    const titleClass = group.title.match(/[Сс]делано/) ? 'done-group' : group.title.match(/[Вв]стреч/) ? 'meetings' : 'doing';
    html += `<div class="group-title ${titleClass}">${esc(group.title)}</div>`;
    for (const task of group.tasks) {
      const doneClass = task.done ? ' done' : '';
      const subClass = task.indent > 0 ? ' sub' : '';
      html += `<div class="task${doneClass}${subClass}" data-line="${task.line}" onclick="toggle(this)">`;
      html += `<div class="checkbox"><span class="checkmark">✓</span></div>`;
      html += `<div class="task-text">${renderInline(task.text)}</div>`;
      html += `</div>`;
    }
    html += `</div>`;
  }

  document.getElementById('content').innerHTML = html;
  updateStatus();
}

async function toggle(el) {
  const line = el.dataset.line;
  el.style.pointerEvents = 'none';

  try {
    const res = await fetch('/api/toggle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({line: parseInt(line)})
    });
    const data = await res.json();
    render(data);
  } catch (e) {
    el.style.pointerEvents = '';
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function renderInline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">$1</a>');
}

function updateStatus() {
  const now = new Date();
  const t = now.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
  document.getElementById('status').textContent = 'Обновлено ' + t;
}

// Initial load + auto-refresh
loadPlan();
refreshTimer = setInterval(loadPlan, 30000);
</script>
</body>
</html>"""

# ─── Server ───

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/plan":
            self.send_json(parse_plan())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/toggle":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            toggle_task(body["line"])
            self.send_json(parse_plan())
        else:
            self.send_error(404)

    def send_json(self, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass  # тихий сервер


if __name__ == "__main__":
    if not PLAN_FILE.exists():
        print(f"Файл не найден: {PLAN_FILE}")
        raise SystemExit(1)

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Day Plan Viewer → {url}")
    print("Ctrl+C чтобы остановить")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
        server.server_close()
