#!/usr/bin/env python3
"""Stop-time compliance backstop дельт meeting-analysis (фикс D).

Контракт вызовов валидатора (validation-contract.json) до этого хука
принуждался только в eval-харнесе: в живой сессии модель сама решала,
звать ли валидатор, который её же проверяет. Хук делает молчаливый
пропуск гейтов Шага 4 L2-procedure-scaffold-update.md ОБНАРУЖИВАЕМЫМ
в Claude Code и принуждает к отзыву выдачи.

ЧТО ЭТО НЕ ТАКОЕ. Событие Stop наступает ПОСЛЕ вывода ответа —
предотвратить первое отображение невалидной выдачи хук не может
(это же причина, почему он не «гейт показа»). Он также НЕ доказывает:
что shell реально запускал валидатор (проверяются наблюдаемые
payload-снимки из транскрипта, а не факт исполнения — конструкция
вида `false && validate_deltas.py ...` с пакетом, реально проходящим
доверенный перепрогон, засчитывается by design: чтобы «обмануть»,
нужно собрать валидный пакет, то есть сделать саму работу); что
ревью/Фаза B выполнялись как стадии мышления; что ТЕКСТ выдачи
совпадает со снимком; что снимки принадлежат текущей встрече. Полное
enforcement (typed ledger, exact HITL, guarded apply) — Этап 1
global-improvement-plan.

Активация: маршрут — по последнему успешному Read L2-процедуры
(scaffold/client; точное имя файла + сегмент meeting-analysis в пути);
показ — оба маркера выдачи Шага 4 («Советую обновить», «Сомневаюсь»)
как заголовки/начала строк в тексте последнего хода. Текст хода
собирается из транскрипта И hook_input.last_assistant_message (на
момент Stop финал может ещё не быть в transcript_path); user-записи,
состоящие только из tool_result, ход НЕ обрывают — «показал и начал
применять» остаётся под гейтом.

Эпизодность: эпизод открывается успешным Read scaffold-процедуры и
закрывается показом. Перечитывание процедуры ВНУТРИ эпизода (сверка
формата до показа) эпизод не сбрасывает; после состоявшегося показа
новый Read открывает новый эпизод с нуля. Сверх того каждый повторный
показ требует нового валидного final|both-вызова ПОСЛЕ предыдущего
показа (семантика Шага 4: показываемый состав = пакет последнего
вызова) — вторая встреча или пересборка выдачи не едут на старом
контракте.

Проверка контракта: stdout вызовов из транскрипта НЕ доверяется —
heredoc-payload каждого наблюдаемого снимка вызова `validate_deltas.py
--phase X` (только quoted-heredoc: unquoted раскрывается шеллом, и
перепрогнан был бы не тот текст) ПОВТОРНО прогоняется доверенным
валидатором соседней раскладки: exit 2 → снимок невалиден
(contract.valid_call); exit 0 → зелёный; exit 1 → валидный красный
(включая краш валидатора — слабость контракта, не хука). Снимок
считается наблюдаемым и при is_error результата — non-zero exit
валиден по контракту, истину о payload даёт перепрогон. Контракт
закрыт: снимков coverage >= 1, final >= 2 (`both` — в обе фазы),
последний валидный final|both зелёный И позже успешного Read
L2-review-procedure.md этого эпизода. Иначе — блок с требованием
отозвать выдачу.

Fail-closed: валидатор не найден при активном scaffold-маршруте —
блок (повреждённая раскладка); контракт присутствует, но битый
синтаксически или структурно — блок (отсутствие файла — дефолты);
исчерпан бюджет времени перепрогона — блок (закрытость не доказана);
contract_version новее известного хуку — блок (рассинхрон установки).
Бюджет: дедуп одинаковых (phase, payload) + окно с гарантией
последнего вызова каждой фазовой группы + общий дедлайн 30с при
внешнем timeout 60с в settings. Перепрогон наследует cwd сессии;
валидатор читает только stdin и на cwd не опирается.

Повторные Stop: `stop_hook_active` НЕ отключает проверку — повторный
показ блокируется снова; цикл размыкается отзывом показа или закрытием
контракта (runtime Claude Code дополнительно прекращает цикл после ~8
блокировок подряд — предел платформы, не хука).

Ограничения v1 (осознанные, полный разбор — карточка
orchestrator-skips-mandatory-gates): активация по транскрипту — перила
против рационализации пропуска, не защита от намеренного обмана
(перефразированная выдача, показ без чтения процедуры или Read
клиентской процедуры посреди scaffold-эпизода снимают гейт);
соответствие ТЕКСТА показанного состава провалидированному пакету не
проверяется (typed ledger / guarded apply — Этап 1
global-improvement-plan); заголовки-цитаты обоих маркеров в начале
строк дадут ложный блок на один ход; экзотические shell-формы вызова
(перенос строки бэкслешем, редирект посреди argv, unquoted heredoc) не
распознаются — консервативный блок, канон Шагов 3.2/3.4 работает;
маркеры повторного показа, существующие только в last_assistant_message
(финал ещё не в транскрипте), событие показа не создают — та же гонка,
что у первичного детекта; вызовы валидатора из субагентов главному
транскрипту невидимы — консервативный блок (вызовы делает координатор).

Только Claude Code (на Cowork хуков нет). Zero context pollution:
stdout только при блокировке.
"""

import argparse
import contextlib
import io
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

PROCEDURE_SCAFFOLD = "L2-procedure-scaffold-update.md"
PROCEDURE_CLIENT = "L2-procedure-client-update.md"
PROCEDURE_REVIEW = "L2-review-procedure.md"
SKILL_DIR_MARKER = "meeting-analysis"
VALIDATOR_MARKER = "validate_deltas.py"
KNOWN_CONTRACT_VERSIONS = (1, 2)
DEFAULT_REQUIRES = {"coverage": 1, "final": 2}
# Бюджет: дедлайн 30с < 60с внешнего timeout хука в settings — срыв по
# времени не превращается в non-blocking hook error, а даёт fail-closed
MAX_REVALIDATIONS = 8
REVALIDATION_TIMEOUT = 5
REVALIDATION_DEADLINE = 30

SHOW_MARKER_RES = (
    re.compile(r"(?m)^[\s>]*#{0,6}\s*\**Советую обновить"),
    re.compile(r"(?m)^[\s>]*#{0,6}\s*\**Сомневаюсь"),
)


def is_show(text):
    return all(rx.search(text) for rx in SHOW_MARKER_RES)
PHASES = ("coverage", "final", "both")
# Зеркало CLI валидатора: та же схема аргументов, что в validate_deltas.py
# main(). Отличие: --help у зеркала отвергается (add_help=False), у
# реального CLI печатает справку без разбора payload — в обоих случаях
# вызов не засчитывается
_CLI_MIRROR = argparse.ArgumentParser(add_help=False)
_CLI_MIRROR.add_argument("--phase", choices=PHASES, required=True)
# Только quoted-heredoc НА СТРОКЕ ВЫЗОВА: <<'TAG' или <<"TAG"
# (unquoted раскрывается шеллом — перепрогнан был бы не тот текст)
HEREDOC_START_RE = re.compile(r"<<(-?)\s*(['\"])([A-Za-z_][A-Za-z0-9_]*)\2")


def skill_file(fp, filename):
    p = fp.replace("\\", "/")
    return (p.rsplit("/", 1)[-1] == filename
            and SKILL_DIR_MARKER in p.split("/"))


def load_contract():
    """("missing"|"damaged"|"ok", dict|None): отсутствие файла — дефолты,
    битый синтаксис/структура — fail-closed (решает main)."""
    contract = (Path(__file__).resolve().parent.parent
                / "skills" / SKILL_DIR_MARKER / "validation-contract.json")
    if not contract.is_file():
        return "missing", None
    try:
        data = json.loads(contract.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "damaged", None
    if not isinstance(data, dict):
        return "damaged", None
    return "ok", data


def validator_path():
    p = (Path(__file__).resolve().parent.parent
         / "skills" / SKILL_DIR_MARKER / VALIDATOR_MARKER)
    return p if p.is_file() else None


def parse_call(command):
    """(phase, payload) вызова валидатора либо None.

    Привязка жёсткая: вызов и quoted-heredoc — на ПЕРВОЙ логической
    строке команды (heredoc из другой команды многострочного Bash не
    приписывается валидатору). argv = shell-токены между
    validate_deltas.py и началом heredoc, целиком через зеркало CLI:
    лишние слова, редиректы, --help, значения вне choices → вызов не
    распознан (реальный CLI отверг бы их exit 2 / help; редирект
    посреди argv — сознательно fail-closed). Heredoc обязан быть
    ПОСЛЕДНИМ элементом строки вызова: хвост после делимитера (слова,
    флаги, редиректы, второй heredoc — реальный CLI получил бы другие
    argv/stdin) → вызов не распознан; хвосты вида 2>&1 или | tee —
    тоже fail-closed, канон Шагов 3.2/3.4 их не использует. Payload —
    строки до терминатора по shell-правилам: `<<` требует точного
    совпадения строки с делимитером, `<<-` допускает табуляцию;
    терминатора нет → не распознан. «Строка вызова» — первая
    физическая строка команды (перенос бэкслешем — fail-closed
    экзотика)."""
    first_line, _, rest = command.partition("\n")
    if VALIDATOR_MARKER not in first_line:
        return None
    m = HEREDOC_START_RE.search(first_line)
    if m is None or first_line.find(VALIDATOR_MARKER) > m.start():
        return None
    if first_line[m.end():].strip():
        return None
    try:
        tokens = shlex.split(first_line[:m.start()])
    except ValueError:
        return None
    idx = next((i for i, t in enumerate(tokens)
                if t.replace("\\", "/").rsplit("/", 1)[-1]
                == VALIDATOR_MARKER), None)
    if idx is None:
        return None
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            ns = _CLI_MIRROR.parse_args(tokens[idx + 1:])
    except SystemExit:
        return None
    dash, delim = m.group(1), m.group(3)
    lines = rest.split("\n")
    for j, ln in enumerate(lines):
        candidate = ln.lstrip("\t") if dash else ln
        if candidate == delim:
            return ns.phase, "\n".join(lines[:j])
    return None


def tool_result_only(content):
    return (isinstance(content, list) and content
            and all(isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in content))


def scan(transcript_path):
    """Один проход по транскрипту.

    route/episode_seq — по последнему УСПЕШНОМУ Read L2-процедуры из
    раскладки скилла; review_seq — успешный Read review-процедуры.
    Вызов попадает в calls, если исполнялся (есть tool_result, включая
    is_error) и содержит quoted-heredoc payload. last_turn обрывается
    только настоящей user-репликой — записи из одних tool_result ход
    не завершают. seq — поблочный.
    """
    route = None
    episode_seq = 0    # начало текущего scaffold-эпизода
    review_seq = None
    seq = 0
    show_seqs = []          # события показа: turn-level счётчики маркеров,
                            # min(двух счётчиков) = число событий хода —
                            # пара сквозь записи, две пары (хоть в одной
                            # записи) = два события
    turn_m1 = turn_m2 = 0
    turn_events = 0
    last_real_user_seq = 0  # последняя настоящая реплика руководителя
    pending_calls = {}  # tool_use_id -> (phase, payload)
    pending_reads = {}  # tool_use_id -> "scaffold" | "client" | "review"
    calls = []          # [{phase, payload, seq}] в порядке исполнения
    last_turn = []

    with open(transcript_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = entry.get("message")
            content = message.get("content") if isinstance(message, dict) else None

            if entry.get("type") == "user":
                if isinstance(content, list):
                    for block in content:
                        seq += 1
                        if not (isinstance(block, dict)
                                and block.get("type") == "tool_result"):
                            continue
                        tid = block.get("tool_use_id")
                        # Вызов исполнялся → считается и при is_error:
                        # exit 1 валиден по контракту, истину о payload
                        # даёт доверенный перепрогон
                        call = pending_calls.pop(tid, None)
                        if call is not None:
                            calls.append({"phase": call[0],
                                          "payload": call[1],
                                          "seq": seq})
                        kind = pending_reads.pop(tid, None)
                        if kind is not None and not block.get("is_error"):
                            if kind == "review":
                                review_seq = seq
                            else:
                                route = kind
                                # Новый эпизод — только если прежний
                                # использован показом; перечитывание до
                                # показа эпизод не сбрасывает
                                if kind == "scaffold" and (
                                        episode_seq == 0
                                        or any(s > episode_seq
                                               for s in show_seqs)):
                                    episode_seq = seq
                else:
                    seq += 1
                if not tool_result_only(content):
                    last_turn = []
                    turn_m1 = turn_m2 = 0
                    turn_events = 0
                    last_real_user_seq = seq
                continue

            if entry.get("type") != "assistant" or not isinstance(content, list):
                continue
            record_texts = []
            for block in content:
                seq += 1
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    if block.get("text"):
                        last_turn.append(block["text"])
                        record_texts.append(block["text"])
                    continue
                if block.get("type") != "tool_use":
                    continue
                inp = block.get("input") or {}
                if block.get("name") == "Read":
                    fp = str(inp.get("file_path", ""))
                    if skill_file(fp, PROCEDURE_SCAFFOLD):
                        pending_reads[block.get("id")] = "scaffold"
                    elif skill_file(fp, PROCEDURE_CLIENT):
                        pending_reads[block.get("id")] = "client"
                    elif skill_file(fp, PROCEDURE_REVIEW):
                        pending_reads[block.get("id")] = "review"
                if block.get("name") == "Bash":
                    parsed = parse_call(str(inp.get("command", "")))
                    if parsed is not None:
                        pending_calls[block.get("id")] = parsed
            # Событие показа — turn-level: маркеры считаются накопительно
            # сквозь записи хода (tool-вызовы не разрывают), число событий =
            # min(счётчиков) — вторая полная пара даёт второе событие и
            # внутри одной записи
            if record_texts:
                joined = "\n".join(record_texts)
                turn_m1 += len(SHOW_MARKER_RES[0].findall(joined))
                turn_m2 += len(SHOW_MARKER_RES[1].findall(joined))
                while turn_events < min(turn_m1, turn_m2):
                    show_seqs.append(seq)
                    turn_events += 1

    return (route, episode_seq, review_seq, show_seqs,
            last_real_user_seq, calls, "\n".join(last_turn))


def revalidation_window(calls):
    """Дедуп одинаковых (phase, payload) + окно с гарантией последнего
    вызова каждой фазовой группы (coverage|both и final|both)."""
    unique = []
    seen = set()
    for c in reversed(calls):
        key = (c["phase"], c["payload"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    unique.reverse()
    # Гарантированные места — последним вызовам фазовых групп; остаток
    # окна добивается свежими. Размер окна не превышает MAX_REVALIDATIONS.
    guaranteed = []
    for group in (("coverage", "both"), ("final", "both")):
        last = next((c for c in reversed(unique) if c["phase"] in group),
                    None)
        if last is not None and last not in guaranteed:
            guaranteed.append(last)
    rest = [c for c in unique if c not in guaranteed]
    fill = rest[-(MAX_REVALIDATIONS - len(guaranteed)):] \
        if MAX_REVALIDATIONS > len(guaranteed) else []
    return sorted(guaranteed + fill, key=lambda c: c["seq"])


def revalidate(calls, vpath):
    """Доверенный перепрогон. Возвращает (results, timed_out).

    Дедуп экономит ПЕРЕПРОГОНЫ, но не вызовы: verdict кэшируется по
    (phase, payload), а в results попадает КАЖДЫЙ вызов эпизода — два
    одинаковых final-вызова (до и после ревью с неизменным пакетом)
    легитимно дают счётчик 2. Вызов, чья пара не попала в окно
    перепрогона, в счётчики не входит (не доказан)."""
    cache = {}
    start = time.monotonic()
    for call in revalidation_window(calls):
        key = (call["phase"], call["payload"])
        if key in cache:
            continue
        if time.monotonic() - start > REVALIDATION_DEADLINE:
            return [], True
        try:
            proc = subprocess.run(
                [sys.executable, str(vpath), "--phase", call["phase"]],
                input=call["payload"], capture_output=True, text=True,
                timeout=REVALIDATION_TIMEOUT)
            rc = proc.returncode
        except (OSError, subprocess.SubprocessError):
            rc = 2
        cache[key] = (rc != 2, rc == 0)
    results = []
    for call in calls:
        verdict = cache.get((call["phase"], call["payload"]))
        if verdict is None:
            continue
        results.append({"phase": call["phase"], "seq": call["seq"],
                        "valid": verdict[0], "ok": verdict[1]})
    return results, False


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason},
                     ensure_ascii=False))
    sys.exit(0)


def main():
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    # stop_hook_active НЕ выключает проверку: гейт обязан срабатывать и на
    # повторном показе; цикл размыкается отзывом показа или закрытием
    # контракта
    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    try:
        (route, episode_seq, review_seq, show_seqs,
         last_user_seq, calls, last_turn) = scan(transcript_path)
    except OSError:
        sys.exit(0)

    # Финал может ещё не быть в transcript_path на момент Stop
    show_text = last_turn + "\n" + \
        str(hook_input.get("last_assistant_message") or "")

    if route != "scaffold" or not is_show(show_text):
        sys.exit(0)

    vpath = validator_path()
    if vpath is None:
        block("HOOK: показ дельт при недоступном validate_deltas.py — "
              "раскладка скилла повреждена, контракт валидатора проверить "
              "невозможно. Останови показ и сообщи руководителю о "
              "повреждённой установке скилла.")

    status, contract = load_contract()
    if status == "damaged":
        block("HOOK: validation-contract.json повреждён (битый JSON или "
              "структура) — контракт проверить невозможно. Останови показ "
              "и сообщи руководителю о повреждённой установке скилла.")
    contract = contract or {}

    _MISSING = object()

    def strict_pos_int(value, default):
        # Строгая схема: отсутствующий ключ — дефолт; явный null, bool,
        # строки, ноль и отрицательные — структурная порча (fail-closed)
        if value is _MISSING:
            return default
        if isinstance(value, bool) or not isinstance(value, int) \
                or value <= 0:
            raise ValueError(repr(value))
        return value

    try:
        version = contract.get("contract_version", _MISSING)
        if version is _MISSING:
            version = None
        elif isinstance(version, bool) or not isinstance(version, int):
            raise ValueError(repr(version))
        if version is not None and version not in KNOWN_CONTRACT_VERSIONS:
            block(f"HOOK: validation-contract.json версии {version} не "
                  f"входит в известные этому хуку {KNOWN_CONTRACT_VERSIONS} "
                  "— установка рассинхронизирована. Останови показ и "
                  "сообщи руководителю.")
        req = contract.get("requires", {})
        requires = {
            "coverage": strict_pos_int(req.get("coverage", _MISSING),
                                       DEFAULT_REQUIRES["coverage"]),
            "final": strict_pos_int(req.get("final", _MISSING),
                                    DEFAULT_REQUIRES["final"])}
    except (AttributeError, TypeError, ValueError):
        block("HOOK: validation-contract.json повреждён структурно — "
              "контракт проверить невозможно. Останови показ и сообщи "
              "руководителю о повреждённой установке скилла.")

    # Эпизодность: считаются только вызовы и ревью текущего эпизода
    episode_calls = [c for c in calls if c["seq"] > episode_seq]
    episode_review = review_seq if (review_seq is not None
                                    and review_seq > episode_seq) else None

    results, timed_out = revalidate(episode_calls, vpath)
    if timed_out:
        block("HOOK: бюджет перепрогона валидатора исчерпан — закрытость "
              "контракта не доказана. Показ дельт не разрешён: сократи "
              "пакет вызовов (дубли payload) либо останови показ и сообщи "
              "руководителю.")

    valid = [r for r in results if r["valid"]]
    coverage = sum(1 for r in valid if r["phase"] in ("coverage", "both"))
    final_calls = [r for r in valid if r["phase"] in ("final", "both")]
    final = len(final_calls)
    last_final_ok = bool(final_calls) and final_calls[-1]["ok"]
    after_review = (episode_review is not None and bool(final_calls)
                    and final_calls[-1]["seq"] > episode_review)
    # Повторный показ требует свежего final|both-снимка после предыдущего
    # показа (Шаг 4: показываемый состав = пакет последнего вызова).
    # Текущий показ (последнее событие текущего хода) предыдущим не
    # считается; два события в одном ходе различаются
    prior_shows = list(show_seqs)
    if prior_shows and prior_shows[-1] > last_user_seq:
        prior_shows.pop()
    last_prior_show = max((s for s in prior_shows if s > episode_seq),
                          default=None)
    after_show = (last_prior_show is None
                  or (bool(final_calls)
                      and final_calls[-1]["seq"] > last_prior_show))

    if coverage >= requires["coverage"] and final >= requires["final"] \
            and last_final_ok and after_review and after_show:
        sys.exit(0)

    block(
        "HOOK: дельты показаны при незакрытом контракте валидатора — "
        "доверенный перепрогон payload'ов эпизода дал: "
        f"coverage {coverage}/{requires['coverage']}, "
        f"final {final}/{requires['final']}, "
        f"последний final|both {'зелёный' if last_final_ok else 'красный или отсутствует'}, "
        f"порядок «после ревью» {'подтверждён' if after_review else 'НЕ подтверждён (ревью не читалось в этом эпизоде или последний вызов раньше него)'}, "
        f"вызов после предыдущего показа {'есть' if after_show else 'ОТСУТСТВУЕТ (повторный показ требует нового final|both-вызова на актуальном пакете)'}. "
        "Гейт показа Шага 4 L2-procedure-scaffold-update.md нарушен. "
        "Отзови показанные дельты сообщением «пайплайн выполнен частично, "
        "дельты не готовы к применению», назови незакрытый шаг и закрой "
        "контракт вызовами validate_deltas.py (Шаги 3.2-3.5) либо явно "
        "останови работу, назвав блокер. Применять дельты запрещено."
    )


if __name__ == "__main__":
    main()
