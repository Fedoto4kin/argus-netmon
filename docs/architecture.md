# Архитектура

## Задача

На Linux (ПК → Wi‑Fi → Keenetic → USB‑модем Yota/Мегафон) отличать уровни ограничений **реального WAN**, а не то, что видно через Throne TUN/прокси.

## Поток данных

```text
Tray (GTK/AppIndicator)
        ▲
        │ state, speed, tooltip
Monitor loop (asyncio + thread)
        │
        ├─ LAN check  → gateway TCP
        ├─ Probes     → whitelist / domestic / open
        ├─ Classifier → LinkState (+ hysteresis)
        ├─ Speed      → short HTTPS download (если open OK)
        └─ Notify     → notify-send только на смене состояния
```

Пробы идут с `SO_BINDTODEVICE` на физический интерфейс (`wlp0s20f3`), чтобы не смотреть мир глазами VPN.

## Лестница состояний

От строже к свободнее:

| Состояние | Условие |
|-----------|---------|
| `NO_LAN` | Не достучались до шлюза роутера |
| `DOWN` | Роутер жив, все внешние корзины мертвы |
| `WHITELIST` | Живёт только allow‑list (госуслуги, ya.ru, …) |
| `RU_ZONE` | Живут RU‑сайты вне WL (esad7, pikabu), иностранное нет |
| `OK` | Иностранные open‑пробы проходят |
| `DEGRADED` | Как `OK`, но скорость ниже порога |

Гистерезис: обычно 2 подряд одинаковых «сырых» результата, прежде чем сменить состояние (OK↔DEGRADED — быстрее).

## Модули (`src/argus_netmon/`)

| Модуль | Роль |
|--------|------|
| `app.py` | CLI, цикл монитора, связка трей ↔ пробы |
| `config.py` | Загрузка YAML |
| `prober.py` | LAN + HTTP(S) пробы, bind to device |
| `state.py` | `LinkState`, классификатор, гистерезис |
| `speed.py` | Оценка скорости по короткому download |
| `tray.py` / `tray_backend.py` | Иконка, меню, тултип |
| `icons.py` | Цвет + бейдж (`WL` / `RU` / `OK` …) |
| `notify.py` | Desktop‑уведомления |
| `autostart.py` | XDG `.desktop` |
| `diag.py` | `--diag`: process path и exit IP |

## Скорость

Не полноценный speedtest: HTTPS GET ~256 KB с `speed.cloudflare.com`, скорость тела ответа в kb/s.  
Меряется только при «открытом» интернете (`open_ok`), раз в N циклов.

## Что дальше (не сделано)

- Keenetic Omni RCI: уровень сигнала / RAT модема (`modem.enabled`)
- Упаковка в бинарь `argus-netmon` (сейчас Python entry point)
