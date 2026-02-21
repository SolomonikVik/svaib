---
title: "UI-дизайн — создание интерфейсов с помощью AI"
source: "https://t.me/polyakov_ai"
source_type: thread
status: raw
added: 2026-02-01
updated: 2026-02-21
review_by: 2026-05-07
tags: [ui, design, lovable, v0, bolt, figma, pencil, mobbin, workflow, cowork, claude-code, frontend-design]
publish: false
version: 5
---

# UI-дизайн

## Кратко

Всё про создание UI с помощью AI: подходы, инструменты, кейсы, фишки. Для solo-разработчиков и небольших команд без выделенного дизайнера. Файл пополняется по мере появления новых кейсов и инструментов.

---

## Инструменты

### Генераторы UI (prompt → работающий код)

| Инструмент | Суть | Стек | Цена | Сайт |
|-----------|------|------|------|------|
| **Lovable** | Full-stack генератор, чистый React-код, экспорт в GitHub | React, Tailwind, Supabase | Free / $25/мес | lovable.dev |
| **v0** | Генератор компонентов от Vercel, силён в отдельных UI-элементах | React, Tailwind, Next.js | Free + платные | v0.app |
| **Bolt.new** | Full-stack в браузере, без локальной установки | React, Node.js, PostgreSQL | Free / $20/мес | bolt.new |

### Дизайн-инструменты

| Инструмент | Суть | Когда использовать | Сайт |
|-----------|------|-------------------|------|
| **Pencil.dev** | Бесконечный canvas прямо в IDE (VS Code, Cursor, Claude Code). .pen файлы (JSON) в git. Код через MCP — точные вектора, не скриншоты | Design-in-IDE: дизайн и код в одном месте, версионируются вместе | pencil.dev |
| **Figma Make** | AI-генератор внутри Figma: промпт/скриншот → прототип | Нужен макет, не код. Или референс для генератора | figma.com/make |
| **Figma MCP** | Figma-контекст доступен в Claude Code, Cursor | Design-to-code: AI видит дизайн и генерирует по нему | — |

### Pencil.dev — design-in-IDE (новая категория)

**Что это:** Бесконечный canvas (как Figma) встроенный прямо в IDE. Не design-to-code (дизайн отдельно → экспорт → код), а design = code — дизайн живёт в репозитории.

**Как работает:**
- Рисуешь на холсте в IDE (или говоришь AI "нарисуй экран")
- Результат — `.pen` файл (JSON с точными координатами, размерами, дизайн-токенами)
- .pen лежит в git → бранчится, мёржится, версионируется вместе с кодом
- Claude Code читает .pen через **MCP** → генерирует React/HTML/CSS по точным данным (не по скриншоту)

**Ключевое отличие от Figma MCP:** Figma MCP передаёт контекст из внешнего инструмента. Pencil — это сам дизайн-инструмент внутри IDE, файлы нативно в git. Нет handoff.

**MCP-точность:** `padding-left: 1rem` в .pen → AI пишет `p-4` в Tailwind. Без угадывания по пикселям.

**Что ещё:** Параллельные AI-агенты (несколько экранов одновременно), подключение баз данных и API к холсту, импорт из Figma (copy-paste, слои и Auto Layout сохраняются).

**Цена:** Pencil бесплатный (early access, февраль 2026). Платишь за AI-подписку (Claude, Cursor).

**Ограничения:** Mac — полноценное приложение. Windows — только VS Code extension. Early access — возможны баги.

**Принципы для качественного результата:** семантические имена слоёв (`pricing-card-container`, не `Frame 42`), Auto Layout вместо абсолютного позиционирования, spacing кратно 4-8px, dual-frame для responsive (390px mobile + 1440px desktop).

### Библиотеки референсов

| Инструмент | Суть | Цена | Сайт |
|-----------|------|------|------|
| **Mobbin** | 500K+ скриншотов реальных приложений, фильтрация по паттернам | Free (ограниченно) + подписка | mobbin.com |
| **Dribbble** | Дизайн-портфолио, менее структурированно чем Mobbin | Бесплатно | dribbble.com |

### Дизайн-токены и кастомизация

| Инструмент | Суть | Сайт |
|-----------|------|------|
| **UI Colors** | Генерация полных палитр (50-950) из одного цвета | uicolors.app |
| **TweakCN** | Визуальный редактор ShadCN тем, экспорт CSS-переменных | tweakcn.com |
| **Tailwind Color Generator** | HSL-совместимые палитры для Tailwind | — |
| **Fontjoy** | Автоматический подбор шрифтовой пары через ML | fontjoy.com |
| **Font Combinations** | Проверенные комбинации шрифтов | — |

### Компонентные библиотеки (Tailwind / ShadCN)

| Библиотека | Суть | Сайт |
|-----------|------|------|
| **Magic UI** | Премиум компоненты с анимациями | magicui.design |
| **Aceternity UI** | Сложные интерактивные элементы | ui.aceternity.com |
| **Awesome ShadCN** | Кастомные компоненты, ресурсы, хелперы | github.com (awesome-shadcn) |

### Claude Code / Cowork как дизайн-инструмент

**Подход:** Дизайн прямо в Claude, без внешних генераторов. Два варианта:

- **Claude Code** — через скилл `frontend-design` (подключается как skill). Меняет стиль вывода: вместо generic AI-лейаутов — более самобытный, "дизайнерский" результат
- **Cowork** — GUI-режим Claude Desktop. По наблюдениям, лучше справляется с UI/дизайном, чем Claude Code (причины неясны, но паттерн устойчивый)

**Workflow прототипирования (Cowork):**
1. Подключить папку проекта
2. Попросить 3-4 HTML-прототипа (именно HTML — чтобы превью работало в Cowork)
3. Указать "используй мой текущий контент и дизайн" — иначе получишь generic
4. Выбрать понравившийся
5. Попросить внедрить в реальный проект (любой фреймворк)
6. Итерировать: секции, анимации, сторителлинг

**Отличие от внешних генераторов:** Не нужен экспорт/импорт — Claude видит проект и работает прямо в нём.

---

## Проблема "AI-слепоты"

AI-генераторы (включая Claude) выдают узнаваемо похожие дизайны: двухколоночные сравнения, одинаковые hero-секции, стандартные card-лейауты. Пользователи и клиенты уже распознают "AI-сделанное".

**Корень проблемы:** Дефолтный Tailwind + ShadCN + промпты без дизайн-требований. "Сделай красиво" не работает — нужна структурированная конкретика.

**Приёмы против:**
- Скилл `frontend-design` — заточен на дизайнерское качество, не generic
- Reverse-дизайн: скриншоты → AI agent → дизайн-токены (референсы > текстовых описаний)
- Своя цветовая схема через CSS-переменные (UI Colors, TweakCN — см. инструменты выше)
- Кастомная типографика (Fontjoy для подбора шрифтовых пар)
- Итерация после первого прохода — первый результат почти всегда generic, ценность в доработке

**Парадокс насмотренности:** Чем меньше дизайн-навыков, тем больше стоит полагаться на готовые качественные блоки и шаблоны (Magic UI, Aceternity UI) — они часто лучше AI-дефолта, потому что делались профессиональными дизайнерами. С хорошей насмотренностью — кастомизируй глубже через дизайн-токены.

**Промпт-шаблоны** (вместо "сделай красиво"):

```
// типографика
Design clear typography hierarchy using modern sans-serif font.
Large heading, medium subheading, readable body text.
Ensure good line spacing and visual rhythm throughout the page.

// UI-компоненты
Create card components with contemporary styling - subtle shadows,
rounded corners, clean white background. Add hover effects
and make them feel interactive and polished.

// цвета
Use professional color palette - primary brand color, neutral grays,
success/error states. Ensure good contrast for accessibility
and maintain consistent color usage across all components.
```

**Design Principles для CLAUDE.md / Cursor Rules:**

```
## Design Principles
- Generous spacing: Use plenty of whitespace, avoid cramped layouts
- Cards: Subtle elevation, consistent padding, avoid heavy borders
- Modern aesthetics: Subtle shadows, rounded corners, clean typography
- Interactive states: Smooth hover effects, button feedback, loading states
- Visual hierarchy: Clear information structure with proper heading levels
- Accessibility: Good color contrast, readable fonts, proper focus states
- Consistent system: Reusable components, unified spacing scale
- Use consistent spacing units (8px, 16px, 24px, 32px)
- Test colors in both light and dark modes
- Implement consistent iconography from a single icon family
```

---

## Кейсы и подходы

### Кейс: UI за 30 минут (Поляков, февраль 2026)

**Источник:** Артём Поляков, канал "Поляков считает — AI, код и кейсы". Один из популярных постов канала.

**Задача:** Обновить стандартный серый UI-компонент (голосовой агент ElevenLabs) до красивого интерфейса.

**Процесс:**

1. **Референсы (5 мин)** — Mobbin → поиск по теме → скачать 1-2 скриншота. Инсайт: скриншоты работают лучше текстовых описаний ("сделай красиво" не работает)
2. **Описание текущего UI** — Claude Code описывает компоненты, состояния, свойства в UI.md. Чтобы новый дизайн не сломал логику
3. **Параллельный запуск (2-3 мин)** — загрузить референсы + описание + промпт в 2-3 генератора одновременно. Результаты непредсказуемы
4. **Выбор лучшего** — у Полякова: Lovable победил, Figma Make неплохо, Antigravity мимо. В других задачах расклад будет другим
5. **Интеграция** — экспорт из генератора в GitHub → Claude Code переносит в проект. Генерация и интеграция — отдельные шаги

**Стоимость:** Mobbin $15/мес + Lovable $20/мес + Claude Code. Дополнительные расходы ~$55 поверх Claude.

---

## Фишки и наблюдения

- Скриншоты-референсы > текстовых описаний для AI-генераторов
- Фиксируй текущее состояние до старта — новый дизайн не должен сломать логику
- Параллельный запуск нескольких генераторов — результаты непредсказуемы, один попадёт
- Интеграция отдельно от генерации — не генерируй прямо в рабочем проекте
- С бэкендом из генераторов хорошо справляется только Antigravity (наблюдение Полякова)
- Готовые компонентные библиотеки (Magic UI, Aceternity UI) > AI-дефолт для тех, кто не дизайнер (@nobilix)
