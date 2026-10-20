---
title: "Установка BB Desktop, Codex CLI и OMP"
created: 2026-10-14
updated: 2026-10-14
status: draft
type: reference
audience: client
publish: false
---

# Установка BB Desktop, Codex CLI и OMP

BB Desktop — приложение с интерфейсом к агентам. Codex CLI — открытый агентный харнес, который устанавливается на тот же компьютер и подключается к BB. OMP (Oh My Pi) — ещё один харнес для дальнейшей проверки. Модель, доступ к ней и плагин svaib настраиваются отдельно.

## 🔹 Что скачать

Используй [последний релиз BB Desktop](https://github.com/get-bb/bb/releases/latest). Выбери файл по своему компьютеру:

| Компьютер | Файл приложения |
| --- | --- |
| Mac с Apple Silicon | `.dmg` с `arm64` в имени |
| Windows x64 | `.exe` с `x64` в имени |
| Linux x64 | `.AppImage` с `x86_64` в имени |

Для Mac Intel десктопной сборки в проверенном наборе релизных файлов нет. Windows и Linux Desktop обозначены разработчиками как alpha; это выбранный маршрут установки. [Платформы BB](https://github.com/get-bb/bb#download-the-desktop-app).

Устанавливаем последние опубликованные версии. После установки сохраняй фактическую версию для диагностики и совместных проверок.

## 🔹 Mac: Apple Silicon

1. В меню Apple → «Об этом Mac» проверь поле «Чип».
2. На [странице последнего релиза](https://github.com/get-bb/bb/releases/latest) скачай `.dmg` с `arm64` в имени.
3. Открой DMG и перенеси BB в Applications («Программы»).
4. Запусти BB из Applications.
5. Проверь `git --version` в Terminal. Если Git отсутствует, установи инструменты Apple командой `xcode-select --install` и после завершения повтори проверку.
6. Установи Codex CLI по разделу ниже.

BB Desktop не требует отдельной установки Node.js для оболочки. [Способы установки BB](https://github.com/get-bb/bb#use-bb).

## 🔹 Windows: Desktop

1. Используй Windows x64; проверенный upstream-маршрут — Windows 11.
2. Установи [Git for Windows](https://git-scm.com/download/win). Открой новый терминал и проверь `git --version`.
3. На [странице последнего релиза](https://github.com/get-bb/bb/releases/latest) скачай `.exe` с `x64` в имени.
4. Запусти установщик, закончи установку и открой BB из меню «Пуск».
5. Установи Codex CLI **в Windows** по разделу ниже.
6. Для первого проекта используй обычную локальную папку. UNC-пути `\\server\share` BB отвергает.

Git for Windows нужен также для bash-скриптов настройки среды. Условия native-host — в [поддержке платформ](https://github.com/get-bb/bb/blob/main/docs/platform-support.md#supported-host-environments).

Открытые upstream-отчёты на дату подготовки инструкции; это сообщения пользователей, а не наши Windows-прогоны:

| Ограничение | Что учитывать |
| --- | --- |
| [Обновление Codex из BB](https://github.com/get-bb/bb/issues/5428) | Отчёт касается native Codex на Windows-host, подключённом к удалённому серверу. Если обновление из BB не стартует, обновлять CLI командой из раздела Codex ниже |
| [Google Drive G:/H: не видны в выборе папки](https://github.com/get-bb/bb/issues/5358) | Сначала проверять локальную папку; запуск на виртуальном диске отдельно |
| [Остановка процесса/следующий ход](https://github.com/get-bb/bb/issues/5195) | Возможны ошибки на границе ходов и ненулевой выход CLI после выполненной команды; состояние проверять до повторения |
| [Bitdefender при подключении машины](https://github.com/get-bb/bb/issues/5451) | Отчёт о регистрации автозапуска host-daemon при enrollment; не доказательство сбоя обычной установки Desktop |

## 🔹 Linux: Desktop AppImage

1. На [странице последнего релиза](https://github.com/get-bb/bb/releases/latest) скачай `.AppImage` с `x86_64` в имени. Сохрани её в домашнюю папку с именем **bb.AppImage**.
2. В терминале установи приложение в `/opt/bb/`:

   ```bash
   sudo install -D -m 755 ~/bb.AppImage /opt/bb/bb.AppImage
   ```

3. Запусти BB обычным пользователем:

   ```bash
   /opt/bb/bb.AppImage
   ```

4. Установи Codex CLI по разделу ниже.

Для AppImage нужна библиотека FUSE 2. Если приложение сообщает об отсутствии `libfuse.so.2`, установи пакет этой библиотеки средствами своего дистрибутива. Пользовательские настройки и история BB по умолчанию хранятся в `~/.bb/`.

Чтобы BB появился в меню приложений, создай `~/.local/share/applications/bb-desktop.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=BB Desktop
Exec=/opt/bb/bb.AppImage
Terminal=false
Categories=Development;
```

Для короткой команды добавь в `~/.bashrc` одну строку:

```bash
alias bb-desktop='/opt/bb/bb.AppImage'
```

В новом терминале запускай `bb-desktop`.

## 🔹 Установка открытого харнеса Codex CLI

Codex CLI — открытый компонент Codex, который BB запускает локально. [Открытые компоненты](https://learn.chatgpt.com/docs/open-source).

Используем официальный npm-пакет `@openai/codex` с тегом `latest`. Если Node.js и npm ещё нет, установи актуальную **Node.js LTS** через [официальную страницу загрузки](https://nodejs.org/en/download), затем открой новый терминал. Для Linux выбери предложенный на этой странице способ установки для своего дистрибутива. Проверь `node --version` и `npm --version`.

**Mac и Linux**, обычный терминал:

```bash
npm install -g @openai/codex@latest
codex --version
codex --help
```

**Windows**, обычный PowerShell:

```powershell
npm.cmd install -g @openai/codex@latest
codex.cmd --version
codex.cmd --help
```

На Windows `.cmd` запускает npm-обёртку без изменения политики PowerShell. После установки открой новый терминал; если команда не найдена, проверь, что каталог глобальных npm-команд доступен в PATH.

Для Linux/macOS глобальный npm-каталог должен быть доступен пользователю для записи. При `EACCES` настрой пользовательскую установку Node/npm и повтори команду. [Установка CLI в официальной документации OpenAI](https://learn.chatgpt.com/docs/codex/cli).

Установка завершена, когда CLI показывает версию и справку. Модельных запросов эти две проверки не выполняют. Доступ к модели и способ авторизации выбираем на следующем этапе; подписка не нужна для самой установки открытого CLI. Сторонние провайдеры подключаются через конфигурацию Codex. [Конфигурация провайдеров](https://learn.chatgpt.com/docs/config-file/config-advanced#custom-model-providers).

Для обновления повтори команду установки с `@latest`, проверь новую версию и перезапусти BB.

## 🔹 Подключение Codex к BB Desktop

1. Полностью закрой BB и снова открой его после установки харнеса.
2. Добавь локальную папку пространства как проект.
3. Открой новый тред и выбери **Codex**.
4. Настрой выбранную модель и провайдера, затем проверь один запрос с чтением локального файла. До этого доступ к модели считается неподтверждённым.

BB использует установленный CLI и его настройки. Плагин svaib устанавливается в харнес отдельным шагом. [Провайдеры BB](https://github.com/get-bb/bb/blob/main/packages/bb-app/README.md#provider-credentials).

## 🔹 OMP на Linux

Если Bun не установлен, выбираем официальный готовый бинарник. Он не требует отдельной установки Bun или npm-пакета; установщик проверяет SHA-256 и `--version` перед сообщением об успехе. [Установщик OMP](https://github.com/can1357/oh-my-pi/blob/main/scripts/install.sh).

```bash
curl -fsSL https://omp.sh/install -o /tmp/omp-install.sh
sh /tmp/omp-install.sh --binary
```

Проверка:

```bash
~/.local/bin/omp --version
~/.local/bin/omp --help
```

Справка и номер установленной версии должны выводиться без ошибки. Первый полноценный запуск распаковывает native-модули в `~/.omp/natives/`; каталог должен быть доступен пользователю для записи.

Если `command -v omp` ничего не показывает, добавь `export PATH="$HOME/.local/bin:$PATH"` в конфигурацию своего shell (`~/.bashrc` для bash), затем открой новый терминал. Саму установку выполняй без `sudo`.

Для нового разговора открой терминал в папке пространства и запусти `omp`. Авторизация провайдера — следующий отдельный шаг. Если актуальный Bun уже есть и нужен npm-путь расширений, upstream рекомендует `bun install -g @oh-my-pi/pi-coding-agent@latest`. Для Alpine/musl нужны также `libstdc++` и `libgcc`. [Варианты OMP](https://github.com/can1357/oh-my-pi/blob/main/README.md#install).

## 🔹 Признак готовности и следующий шаг

BB установлен, когда интерфейс открывается, локальный проект добавляется, а подготовленный харнес доступен для нового треда. Codex CLI и OMP установлены, когда версия и справка запускаются без ошибки. Эти проверки ещё не доказывают ответ реальной модели или работу svaib.

Далее отдельно проверяем доступность и оплату провайдера из России, подключение модели, установку методологического плагина, MCP-авторизацию, хуки и полный рабочий сценарий. Плагин интерфейса BB и пакет svaib для харнеса устанавливаются независимо. Одной успешной установки оболочки недостаточно для утверждения «работает без VPN и зарубежных карт».
