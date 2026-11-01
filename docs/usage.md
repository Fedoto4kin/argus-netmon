# Использование

## Установка

```bash
cd /path/to/network-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Зависимости ОС:

- `libnotify-bin` (`notify-send`)
- для тултипа в трее (желательно): `gir1.2-ayatanaappindicator3-0.1` + системный `python3-gi`  
  (приложение само подхватывает system site‑packages для `gi`, если они есть)

Скопируйте и поправьте конфиг:

```bash
cp config.example.yaml config.yaml
# или: ~/.config/argus-netmon/config.yaml
```

## Команды

| Команда | Назначение |
|---------|------------|
| `argus-netmon` | Трей + фоновый мониторинг |
| `argus-netmon -v` | То же с подробным логом |
| `argus-netmon --once -v` | Один цикл в stdout, без трея |
| `argus-netmon --diag` | Process identity + IP/probes |
| `argus-netmon --demo-tray` | Цикл всех иконок/тултипов в трее (без сети) |
| `argus-netmon --demo-tray --demo-interval 3` | То же, смена состояния каждые 3 с |
| `argus-netmon --autostart on\|off\|status` | XDG autostart |
| `argus-netmon -c PATH` | Явный конфиг |

Эквивалент: `python -m argus_netmon …`.

## Трей

- Цветной кружок + бейдж: `LAN` / `DN` / `WL` / `RU` / `OK` / `3G`
- Тултип:

```text
Argus
Status: …
Speed: …
```

- Меню: статус, скорость, detail, Check now, Start at login, Quit
- Уведомления — только при смене состояния (в т.ч. «whitelist off», переход RU→full)

## Автозапуск

Меню → **Start at login** или CLI `--autostart on`.  
Файл: `~/.config/autostart/argus-netmon.desktop` (после логина в графическую сессию).

## Типичные проблемы

| Симптом | Что проверить |
|---------|----------------|
| Всегда `OK` при белых списках в браузере | Bind выключен / трафик через прокси; `--diag`, Throne Direct |
| Всегда `WHITELIST`/`RU_ZONE` при нормальной сети | Open‑хосты; Throne/DNS; перезапуск после смены конфига |
| Нет тултипа | GTK/AppIndicator; пакет ayatana GIR; бейдж на иконке всё равно есть |
| Краш Xorg / latin-1 | Старые юникод‑символы в title; используйте актуальный код |
| Скорость пустая | Нормально в WL/RU: Cloudflare часто недоступен; замер только при open OK |
