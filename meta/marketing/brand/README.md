---
title: "brand — визуальная идентичность svaib"
updated: 2026-05-15
version: 1
scope: marketing
type: reference
---

# brand — визуальная идентичность svaib

Ядро бренда (палитра, типографика, логотип, tone of voice) и канальные дизайн-гайды: слайды, PDF, schemes, standalone HTML, сайт, иллюстрации. Источник правды визуальной идентичности.

## Содержимое папки

| Файл | Миссия | Когда читать |
|------|--------|--------------|
| [brand.md](brand.md) | Ядро бренда (v1): палитра, логотип, философия, tone of voice, универсальные правила | Любая визуальная задача — начинать отсюда |
| [Brandbook.html](Brandbook.html) | Черновик брендбука v2 (WIP), главная svaib.com уже на нём | Развитие новой системы, синхронизация v1 → v2 |
| [brand-design-presentation.md](brand-design-presentation.md) | Дизайн-гайд для слайдов: шрифты, размеры, лейауты, brand markers | Делаешь презентацию (PPTX, Marp) |
| [brand-design-pdf.md](brand-design-pdf.md) | Дизайн-гайд для PDF: принципы, шрифты, элементы, антипаттерны | Делаешь оффер, протокол, инсайт-доку |
| [brand-design-diagrams.md](brand-design-diagrams.md) | Схемы-картинки через HTML → Puppeteer → PNG/PDF: стек, протокол | Делаешь диаграмму для поста или документа |
| [brand-design-html.md](brand-design-html.md) | Standalone HTML-артефакты: клиентские intro, методологические схемы | Делаешь самостоятельный HTML-файл (не сайт, не статичная схема) |
| [brand-design-web.md](brand-design-web.md) | Принципиальные решения для сайта (stub, отсылает к `dev/`) | Меняешь сайт — затем уходишь в `dev/dev_context/design_system.md` |
| [brand-design-illustrations.md](brand-design-illustrations.md) | Промпт арт-директора, шаблон генерации картинок, библиотека форм | Генерируешь иллюстрацию для слайда/материала |

## Маршруты чтения

| Триггер задачи | Что читать |
|---|---|
| Делаю слайды | [brand.md](brand.md) → [brand-design-presentation.md](brand-design-presentation.md) → [brand-design-illustrations.md](brand-design-illustrations.md) |
| Делаю PDF (оффер, протокол) | [brand.md](brand.md) → [brand-design-pdf.md](brand-design-pdf.md) → шаблоны в [../_examples/](../_examples/) |
| Делаю схему-картинку для поста | [brand.md](brand.md) → [brand-design-diagrams.md](brand-design-diagrams.md) |
| Делаю standalone HTML | [brand.md](brand.md) → [brand-design-html.md](brand-design-html.md) |
| Меняю палитру / правила | [brand.md](brand.md) (затем проверить согласованность канальных гайдов) |
| Развиваю v2 | [Brandbook.html](Brandbook.html) |

## Связанные контексты

- [../strategy.md](../strategy.md) — маркетинговая стратегия (позиционирование, каналы, воронка)
- [../_examples/](../_examples/) — эталонные HTML-шаблоны для PDF и диаграмм
- [../demos/](../demos/) — HTML-демо продукта (используют этот бренд)
- [../../../dev/dev_context/design_system.md](../../../dev/dev_context/design_system.md) — техническая дизайн-система сайта (CSS, компоненты)
- [../../../.claude/skills/presentation/SKILL.md](../../../.claude/skills/presentation/SKILL.md) — реализация бренда в PPTX
- [../../../lab/tooling-registry.md](../../../lab/tooling-registry.md) — `marp-slides` (markdown-first слайды по этому бренду)
