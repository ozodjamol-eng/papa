"""Проверка чужого скилла на скрытые команды (PAPA). Только читает файлы, ничего не запускает.
Использование: python3 -I scan.py <папка_скилла> [ещё папки...]
Выход: список находок по файлам; код 1, если есть ❌ (опасно)."""
import re, sys, unicodedata
from pathlib import Path

SOFT = {0x200D: "ZWJ (бывает в эмодзи)", 0x200E: "LRM", 0x200F: "RLM", 0xFE0F: "emoji-selector"}  # ⚠️, не ❌
INVISIBLE = {**{c: "zero-width" for c in range(0x200B, 0x200D)}, **{c: "word-joiner/invisible" for c in range(0x2060, 0x2065)},
             0xFEFF: "BOM/zero-width", **{c: "bidi-override" for c in range(0x202A, 0x202F)},
             **{c: "bidi-isolate" for c in range(0x2066, 0x206A)}, 0x00AD: "soft-hyphen"}
DANGER = [  # (уровень, шаблон, пояснение)
    ("❌", r"curl[^\n|]*\|\s*(ba|z)?sh|wget[^\n|]*\|\s*(ba|z)?sh|iex\s*\(|Invoke-Expression", "скачать и сразу выполнить"),
    ("❌", r"(do\s*n[o']?t|never|without)\s+(ask|tell|inform|notify)(ing)?\s+(the\s+)?user|не\s+(спрашивай|говори|сообщай)\s+пользовател", "скрыть действие от пользователя"),
    ("❌", r"ignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompt)|игнорируй\s+(предыдущ|системн)", "обход инструкций"),
    ("❌", r"(api[_-]?key|token|secret|password|\.env|id_rsa|\.ssh)[^\n]{0,60}(send|post|upload|curl|fetch|requests\.)", "вывоз секретов"),
    ("⚠️", r"\b(eval|exec)\s*\(|subprocess|os\.system|child_process|spawn\(", "запуск кода/команд"),
    ("⚠️", r"\bsudo\b|rm\s+-rf|bash\s+-c|base64\s+-d|chmod\s+\+x|git\s+clone|\bnc\s+-", "опасная команда оболочки"),
    ("⚠️", r"<!--", "HTML-комментарий (скрытый текст для ИИ?)"),
    ("⚠️", r"pip\s+install|npm\s+(i|install)\b|brew\s+install|apt(-get)?\s+install", "установка пакетов"),
    ("⚠️", r"urllib|requests\.(get|post)|fetch\(|https?\.request|socket\.", "сетевой запрос в коде"),
    ("⚠️", r"base64\.b64decode|atob\(|[A-Za-z0-9+/]{200,}={0,2}", "закодированный блок"),
    ("⚠️", r"(silently|quietly|automatically)\s+(download|update|install|run|execute)|скачай\s+обновлени", "тихое скачивание/запуск"),
    ("⚠️", r"\?(ref|aff|via|utm_[a-z]+)=|affiliate|партн[её]рск", "партнёрская/рекламная ссылка"),
]
URL = re.compile(r"https?://[^\s)\]>'\"`]+")


def scan(root: Path):
    found, urls = [], set()
    for f in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        if f.is_symlink():
            found.append(("⚠️", f, 0, "символическая ссылка — куда ведёт? (не читаю)")); continue
        try:
            text = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            found.append(("⚠️", f, 0, "бинарный/не UTF-8 файл — смотреть вручную")); continue
        for n, line in enumerate(text.splitlines(), 1):
            for i, ch in enumerate(line):
                o = ord(ch)
                if o == 0xFEFF and n == 1 and i == 0:
                    continue  # BOM в начале файла — норма
                if o in SOFT:
                    found.append(("⚠️", f, n, f"невидимый символ U+{o:04X} ({SOFT[o]})")); break
                if o in INVISIBLE or 0xE0000 <= o <= 0xE007F or 0xE0100 <= o <= 0xE01EF or 0xFE00 <= o <= 0xFE0E:
                    found.append(("❌", f, n, f"невидимый символ U+{o:04X} ({INVISIBLE.get(o, 'tag/variation-char')})")); break
            for lvl, pat, why in DANGER:
                if re.search(pat, line, re.I):
                    found.append((lvl, f, n, f"{why}: {line.strip()[:120]}"))
            urls.update(u.rstrip(".,;:") for u in URL.findall(line))
    return found, urls


def main(dirs):
    bad = False
    for d in dirs:
        root = Path(d)
        found, urls = scan(root)
        verdict = "❌ опасно" if any(x[0] == "❌" for x in found) else ("⚠️ смотреть замечания" if found else "✅ чисто")
        bad |= verdict.startswith("❌")
        print(f"== {root.name}: {verdict}")
        for lvl, f, n, why in found:
            print(f"  {lvl} {f.relative_to(root)}:{n} — {why}")
        hosts = sorted({re.sub(r"^https?://([^/]+).*", r"\1", u) for u in urls})
        if hosts:
            print("  ссылки на:", ", ".join(hosts))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:] or ["."])
