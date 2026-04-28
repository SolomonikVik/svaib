---
marp: true
theme: default
paginate: true
footer: 'svaib<span style="color:#FF4D8D">.</span>'
style: |
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Roboto:wght@400;500&display=swap');

  :root {
    --teal-dark: #008B7F;
    --teal-bright: #00B4A6;
    --pink: #FF4D8D;
    --blue-dark: #2C3E50;
    --yellow: #FFD600;
    --gray: #6B7280;
    --bg: #FFFFFF;
    --bg-alt: #F0FDFB;
    --card: #E0F7F5;
  }

  section {
    background: var(--bg);
    color: var(--blue-dark);
    font-family: 'Roboto', sans-serif;
    font-weight: 400;
    padding: 48px 90px 60px 90px;
    position: relative;
  }

  section::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--teal-dark);
  }

  h1 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 2em;
    color: var(--teal-dark);
    line-height: 1.15;
    margin: 0 0 0.6em 0;
  }
  h2 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 1.45em;
    color: var(--blue-dark);
    margin: 0 0 0.5em 0;
  }
  h3 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 0.75em;
    color: var(--gray);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin: 0 0 0.4em 0;
  }
  h4 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 1em;
    color: var(--blue-dark);
    margin: 0 0 0.4em 0;
  }

  p, li { font-size: 1em; line-height: 1.5; color: var(--blue-dark); }
  small, .caption { font-size: 0.7em; color: var(--gray); }
  strong, .ai { color: var(--pink); font-weight: 800; }

  section.lead {
    background: var(--bg-alt);
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    text-align: center;
  }
  section.lead h1 { font-size: 3.4em; }
  section.lead h2 {
    font-size: 1.4em;
    color: var(--blue-dark);
    font-weight: 400;
    font-family: 'Roboto', sans-serif;
  }

  section.divider {
    background: var(--bg-alt);
    display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
  }
  section.divider h1 { font-size: 2.6em; }

  ul, ol { padding-left: 1.2em; }
  li { margin-bottom: 0.4em; }
  li::marker { color: var(--teal-dark); }

  blockquote {
    border-left: 4px solid var(--teal-bright);
    padding: 0.4em 1.2em;
    color: var(--blue-dark);
    font-style: italic;
    font-size: 1.05em;
    margin: 1em 0;
  }

  .metric-card {
    background: var(--bg);
    border: 1px solid var(--card);
    border-radius: 12px;
    padding: 1.2em 1.4em;
    position: relative;
    overflow: hidden;
  }
  .metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--teal-dark), transparent);
  }
  .metric-card .value {
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 2.4em;
    color: var(--pink);
    line-height: 1.1;
  }
  .metric-card .label {
    font-size: 0.7em;
    color: var(--gray);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  .tag {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 0.55em;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    background: var(--card);
    color: var(--teal-dark);
    border: 1px solid var(--teal-bright);
  }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.2em; }
  .grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1em; }

  .stage {
    background: var(--bg-alt);
    border-radius: 10px;
    padding: 1em 1.1em;
    border-top: 2px solid var(--teal-dark);
  }
  .stage .num {
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 1.6em;
    color: var(--teal-dark);
    line-height: 1;
  }
  .stage .name {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 0.95em;
    color: var(--blue-dark);
    margin-top: 0.4em;
  }

  .panel {
    background: var(--bg-alt);
    border-radius: 10px;
    padding: 1.1em 1.3em;
  }
---

<!-- _class: lead -->

# Руководитель в новой<br>эпохе <span class="ai">AI</span>

## На что опираться, чтобы не вылететь на обочину

---

<!-- _class: divider -->

### Часть первая

# Три вещи, которые<br>говорят на каждом углу.<br>Но без них — никуда.

---

### Очевидное · 1 из 3

# Контекст решает всё

<div class="grid-2">

<div>

<div class="metric-card">
<div class="label">AI без вашего контекста</div>
<div class="value">10%</div>
<small>столько силы вы получаете «из коробки»</small>
</div>

</div>

<div>

AI без контекста — умный незнакомец на улице. Спросишь — ответит чем-то усреднённым.

AI с вашим контекстом (ценности, проект, цели, люди) — сотрудник, проработавший у вас годы.

<blockquote>Управление в эпоху <span class="ai">AI</span> = упаковка контекста.</blockquote>

</div>

</div>

---

### Очевидное · 2 из 3

# Качество запроса = качество ответа

80% жалоб «AI тупой» — это вопрос на троечку.

<div class="grid-2">

<div class="panel">

#### Короткий вопрос

Попса из коуч-журнала. Усреднённый ответ ни про что.

</div>

<div class="panel">

#### Развёрнутая задача

Рабочий ответ под вашу ситуацию, цели и людей.

</div>

</div>

<blockquote>Хорошие промпты пишут не самые технические,<br>а самые управленчески опытные.</blockquote>

---

### Очевидное · 3 из 3

# AI встроен в фреймворк. А не сбоку

<div class="grid-2">

<div class="panel">

#### Как у большинства

«Когда вспомнил». Открыл чат → задал вопрос → закрыл.

<small>Остаётся забавой. Системы не появляется.</small>

</div>

<div class="panel">

#### Как должно быть

Регулярный инструмент управления, встроенный в рутину: встречи, планы, протоколы, цели.

<small>Меняет то, как вы работаете с контекстом.</small>

</div>

</div>

---

<!-- _class: divider -->

### Часть вторая

# Три вещи, которые<br>обычно не говорят.<br>А именно они меняют картину.

---

### Неочевидное · 1 из 3

# Память AI — не в чате. В ваших файлах

Любой длинный диалог проходит четыре фазы:

<div class="grid-4">

<div class="stage">
<div class="num">1</div>
<div class="name">Ничего<br>не знаю</div>
</div>

<div class="stage">
<div class="num">2</div>
<div class="name">Погружение</div>
</div>

<div class="stage">
<div class="num">3</div>
<div class="name">Золотое<br>время</div>
</div>

<div class="stage">
<div class="num">4</div>
<div class="name">Лоботомия</div>
</div>

</div>

<blockquote>Один чат — одна задача. Закрытый чат — нормальный исход.<br>Память живёт в файлах. Markdown — родной язык <span class="ai">AI</span>.</blockquote>

---

### Неочевидное · 2 из 3

# Галлюцинирует с тем же азартом, с каким отвечает правильно

<div class="grid-2">

<div>

AI не «понимает» и не «знает». Он считает вероятность следующего слова.

Поэтому не врёт намеренно — собирает заново каждый раз. Иногда попадает. Иногда промахивается с тем же выражением лица.

</div>

<div class="panel">

#### Новая компетенция руководителя

**Верификация.**

Не «доверять или не доверять» в целом. А — где проверить, где принять, где отдать без проверки.

</div>

</div>

---

### Неочевидное · 3 из 3

# Точка роста — не «что добавить». А «как связать»

<div class="grid-2">

<div>

#### У вас уже есть

- бит-ассистент
- Bitslink — автопротоколист
- внутренняя AI Lab
- DeepSeek в эпизодическом режиме

</div>

<div>

#### Чего не хватает

Связки. Чтобы протокол встречи обновлял базу знаний, профайлы людей, планы и цели — а не лежал отдельным файлом.

</div>

</div>

<blockquote>Сила не в количестве инструментов. Сила — в системе.</blockquote>

---

<!-- _class: divider -->

### Финал

# Что сделать<br>в понедельник утром

---

# Понедельник, 9:00 — три шага

<div class="grid-3">

<div class="stage">
<div class="num">1</div>
<div class="name">Выбрать одну рутину</div>
<small>Встреча 1-на-1, планёрка, протокол клиенту. Ту, что повторяется каждую неделю.</small>
</div>

<div class="stage">
<div class="num">2</div>
<div class="name">Упаковать контекст в файлы</div>
<small>Ценности, цели, профайлы команды, история этой рутины. Markdown, не Word.</small>
</div>

<div class="stage">
<div class="num">3</div>
<div class="name">Запустить регулярный режим</div>
<small>Каждую неделю — один и тот же сценарий. Не «когда вспомнил». По расписанию.</small>
</div>

</div>

<blockquote>Через месяц у вас будет не «AI-помощник».<br>У вас будет другой способ работать.</blockquote>

---

<!-- _class: lead -->

# Спасибо

## Вопросы и продолжение

<small>Виктор Соломоник · svaib · Second AI Brain</small>
