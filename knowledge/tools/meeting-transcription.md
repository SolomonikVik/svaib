---
title: "Запись и транскрибация встреч — обзор инструментов"
source: "https://www.granola.ai/blog/granola-mcp"
source_type: article
status: processed
added: 2026-02-11
updated: 2026-02-11
review_by: 2026-05-11
tags: [meeting, transcription, audio, granola, mcp]
publish: false
version: 1
---

# Запись и транскрибация встреч

## Кратко

Обзор инструментов для записи, транскрибации и анализа встреч — коммерческих и open-source. Тема напрямую связана с продуктом SVAIB (AI-помощник по командным встречам). Включает meeting note-takers (Granola, Otter, Fireflies), open-source STT (Sherpa-ONNX, T-one, Hyprnote) и сравнительные ресурсы.

---

## Коммерческие продукты

**[Granola](https://www.granola.ai/)** — AI-блокнот для встреч: записывает системный аудио (без бота), совмещает ручные заметки с AI-транскрипцией. Mac + iPhone. Zoom/Meet/Teams/Webex/Slack. Free (25 встреч), Individual $18/мес, Business $14/user/мес, Enterprise $35/user/мес. Февраль 2026: запустили [MCP-интеграцию](https://www.granola.ai/blog/granola-mcp) — заметки встреч доступны из Claude, ChatGPT, Cursor через `https://mcp.granola.ai/mcp`. Популярен среди VC и консультантов.

**[Bluedot](https://www.bluedothq.com/)** — запись + транскрипция + CRM-интеграция. Chrome-расширение + десктоп (Mac/Win) + мобильное (iOS/Android). Без бота в звонке. 100+ языков. Интеграции: HubSpot, Salesforce, Pipedrive, Slack, Notion. Free (5 встреч), далее платно. 50K+ компаний.

**[Otter.ai](https://otter.ai/)** — один из пионеров AI-транскрибации. Точность ~95%. Conversational search — можно задавать вопросы по содержимому встреч. Zoom/Meet/Teams. Сильная позиция на рынке.

**[Fireflies.ai](https://fireflies.ai/)** — established meeting assistant. Бот в звонке или Chrome-расширение. Пушит саммари в Slack, Notion, CRM. 5000+ интеграций через Zapier.

**[tl;dv](https://tldv.io/)** — запись + транскрипция + сниппеты из встреч. 30+ языков. Удобно делиться фрагментами. Бесплатный tier достаточно щедрый.

**[Fathom](https://fathom.video/)** — бесплатный AI meeting assistant с неограниченной записью. Zoom/Meet/Teams. Автоматические саммари и action items.

---

## Open-source и developer tools

**[Hyprnote](https://hyprnote.com/)** — open-source AI-блокнот для встреч. YC S25. Mac (Apple Silicon). Локальная обработка, данные на устройстве, markdown-файлы. Выбор STT-провайдера и LLM. Прямой open-source аналог Granola. [GitHub](https://github.com/hyprnote/hyprnote)

**[Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx)** — универсальный toolkit для работы с аудио: STT, TTS, diarization, speaker ID/verification, VAD, keyword spotting, source separation, audio tagging. 12 языков программирования (C++, Python, JS, Swift, Kotlin, Go, Rust и др.). Работает на всём — от Raspberry Pi до серверов. 100% offline. Заточен под локальный запуск на устройствах.

**[T-one](https://github.com/voicekit-team/T-one)** (Тинькофф/T-tech) — streaming ASR для русского языка. Conformer-CTC, 71M параметров. WER 5.8-8.6% на телефонии. Apache 2.0. Только русский, оптимизирован под телефонию и call-центры. [HuggingFace](https://huggingface.co/t-tech/T-one)

---

## Сравнительные ресурсы

- [Подробная таблица транскрайберов для Mac](https://docs.google.com/spreadsheets/d/1JqyglRJXzxaj8OcQw9jHabxFUdsv9iWJXMPXcL7On0M/edit?gid=863268287#gid=863268287) — community-сравнение по фичам, точности, цене

---

## Связанные файлы

- [cowork.md](cowork.md) — Fireflies как плагин Cowork
- [../../meta/meta_context/product_vision.md](../../meta/meta_context/product_vision.md) — вижен продукта SVAIB (AI-помощник по встречам)
