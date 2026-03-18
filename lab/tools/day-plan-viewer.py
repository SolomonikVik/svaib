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
<style>
:root {
  --bg: #FAFBFC;
  --surface: #FFFFFF;
  --border: rgba(0, 0, 0, 0.08);
  --text: #1A1A1A;
  --muted: #6B7280;
  --accent: #00B4A6;
  --pink: #FF4D8D;
  --done-text: #9CA3AF;
  --radius: 16px;
  --font-ui: "Inter", "Roboto", "Segoe UI", sans-serif;
  --font-display: "Montserrat", "Inter", sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-ui);
  color: var(--text);
  background: var(--bg);
  border-top: 3px solid var(--accent);
  min-height: 100vh;
  padding: 32px 20px;
}

.container {
  max-width: 520px;
  margin: 0 auto;
}

.header {
  font-family: var(--font-display);
  margin-bottom: 28px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.header .date {
  font-size: 16px;
  color: var(--muted);
  font-style: italic;
}

.group {
  margin-bottom: 24px;
}

.group-title {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin-bottom: 10px;
  padding-left: 4px;
}

.group-title.doing {
  color: var(--pink);
}

.group-title.done-group {
  color: var(--accent);
}

.task {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 8px;
  cursor: pointer;
  transition: transform 0.12s, box-shadow 0.12s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.task:active {
  transform: scale(0.98);
}

.task:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.task.done {
  opacity: 0.6;
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
  border-radius: 7px;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  transition: background 0.15s, border-color 0.15s;
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
  line-height: 1.45;
  padding-top: 1px;
}

.status {
  text-align: center;
  font-size: 12px;
  color: var(--muted);
  margin-top: 32px;
  opacity: 0.6;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--muted);
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
    const titleClass = group.title.match(/[Сс]делано/) ? 'done-group' : 'doing';
    html += `<div class="group-title ${titleClass}">${esc(group.title)}</div>`;
    for (const task of group.tasks) {
      const doneClass = task.done ? ' done' : '';
      const subClass = task.indent > 0 ? ' sub' : '';
      html += `<div class="task${doneClass}${subClass}" data-line="${task.line}" onclick="toggle(this)">`;
      html += `<div class="checkbox"><span class="checkmark">✓</span></div>`;
      html += `<div class="task-text">${esc(task.text)}</div>`;
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
