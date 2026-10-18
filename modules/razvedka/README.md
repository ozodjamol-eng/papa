# Razvedka — разведка каналов-источников и конкурентов (фаза 1)

Читает каналы из папок Telegram (`config.toml`) и свои каналы, считает:
лучшие часы и дни, силу форматов, лидеров по просмотрам и ERR, вероятную рекламу у конкурентов,
самые сильные посты. Отчёт — в канал «PAPA ОТЧЁТЫ» 4 картинками (с 18.10, `razvedka/cards.py`; запасной путь — текст), в «Избранное» не шлём. Досье больших каналов — `dossier` (по понедельникам само).

- Только чтение. Единственная запись — отчёт в «Избранное» своего же аккаунта.
- Работает на Франкфурте под пользователем `papa-razvedka`, сессия Telegram — `/etc/papa-razvedka/telegram.env` (root, 0600).
- Задачи: `papa-update razvedka-install | razvedka-login | razvedka-collect | razvedka-report | razvedka-auto`.
- Тесты: `python3 -m unittest tests/test_razvedka.py` (без внешних зависимостей).
