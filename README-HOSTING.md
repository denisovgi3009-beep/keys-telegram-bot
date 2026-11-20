# Заливка бота на хостинг (amwera.com и любой Python-хостинг)

`amwera.com` — это хостинг игровых/бот-серверов на панели **Pterodactyl**. Для Python-бота
нужен тариф **«бот-хостинг / Python»** (не Minecraft-сервер). Ниже — 3 способа, выбери свой.

---

## Что должно быть в архиве (уже готово в этой папке)
```
bot.py  main.py  db.py  config.py  seed_keys.py
requirements.txt  start.sh  Procfile  runtime.txt
Dockerfile  docker-compose.yml  .env.example  .gitignore  .dockerignore
```
⚠️ **Не грузи в сеть файл `.env` с настоящим токеном** — токен задавай переменными окружения
в панели (см. ниже). В репозиторий/архив `.env` не попадает (уже в `.gitignore`).

---

## Способ A — Pterodactyl-панель (то, что у amwera)

1. **Создай сервер** с «яйцом» **Python** (или «Generic Bot / Python»). В поле *Startup Command*
   поставь:
   ```
   python bot.py
   ```
   (если требуют `main.py` — тоже сработает: `python main.py`).
   Версию Python выбери **3.10 / 3.11**.

2. **Переменные окружения** во вкладке *Variables* (или *Environment*):
   | Имя | Значение |
   |-----|----------|
   | `BOT_TOKEN` | твой токен от @BotFather |
   | `ADMIN_IDS` | `8986267967` |

   Бот читает их из окружения (`config.py`), файл `.env` на сервере **не нужен**.

3. **Загрузи файлы** через *File Manager* или по **SFTP** (данные FTP/SFTP панель показывает
   в карточке сервера: Host, Port, Username, Password). Закачай все `.py`, `requirements.txt`
   и `start.sh`. `store.db` можно не качать — он создастся сам.

4. **Зависимости.** В нормальных Python-яйцах есть шаг сборки, который сам делает
   `pip install -r requirements.txt` при старте. Если сборка не запускается автоматически —
   стартовая команда `bash start.sh` поставит их и запустит бота.

5. **Старт.** Нажми *Start*. В логе должно появиться:
   ```
   Связь с Telegram OK. Бот: @твой_бот ...
   ```
   Если видно предупреждение про `api.telegram.org` — значит этот тариф/узел **не пускает к
   Telegram**. Напиши в поддержку amwera: «нужен исходящий доступ к api.telegram.org:443».

6. **Ключи на склад** — без консоли, прямо из чата (боту-админу):
   ```
   /addkeys 30d NLE-XXXX... NLE-YYYY...
   /addkeys 90d NLE-....
   ```
   `id` товаров: `30d`, `90d`, `180d`, `1y` (показать: `/stock`).

---

## Способ B — VPS (Ubuntu/Debian) у amwera или где угодно

```bash
sudo apt update && sudo apt -y install python3 python3-venv
# залей папку telegram-bot/ (scp/sftp/гит) и внутри:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # впиши BOT_TOKEN и ADMIN_IDS
python bot.py
```
Чтобы работал в фоне после выхода:
```bash
pip install -U tmux
tmux new -s bot 'python bot.py'   # Ctrl+B, затем D — отцепить
# вернуть: tmux attach -t bot
```
Или systemd-юнит (`/etc/systemd/system/nlbot.service`):
```ini
[Unit]
Description=Neverlose keys bot
After=network.target
[Service]
WorkingDirectory=/opt/telegram-bot
Environment=BOT_TOKEN=... 
Environment=ADMIN_IDS=8986267967
ExecStart=/opt/telegram-bot/.venv/bin/python bot.py
Restart=always
[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now nlbot
journalctl -u nlbot -f
```

---

## Способ C — Docker (любой хост с Docker)

```bash
cp .env.example .env      # впиши BOT_TOKEN, ADMIN_IDS
docker compose up -d --build
docker compose logs -f
```
Склад (`store.db`) переживает пересборку — лежит в томе `./data`.

---

## Частые проблемы
- **`ModuleNotFoundError: aiogram`** — не установились зависимости. Запусти
  `bash start.sh` или `pip install -r requirements.txt`.
- **Бот молчит / нет `Связь с Telegram OK`** — хостинг блокирует исходящие к Telegram.
  Это решается только поддержкой хостинга (открой тикет) или сменой тарифа/узла.
- **Не приходят уведомления об оплатах** — проверь `ADMIN_IDS` и что ты написал боту
  `/start` (бот не может прислать первым — нужно, чтобы ты начал диалог).
- **Панель требует открытый порт** — боту порт не нужен (long polling). Если очень просят,
  переключимся на **webhook** (нужен публичный HTTPS-адрес этого сервера) — скажи, допишу.

## Безопасность токена
Токен = полный контроль над ботом. Не свети его в чатах/скриншотах. Если засветился —
отзови новый через @BotFather (`/revoke`) и обнови `BOT_TOKEN`.
