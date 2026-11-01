# argus-netmon

Трей‑монитор сети для Linux: состояние линка, уровни ограничений мобильного интернета (Yota/Мегафон) и грубая оценка скорости. Пробы смотрят **реальный WAN** (мимо Throne TUN).

## Документация

| Документ | О чём |
|----------|--------|
| [docs/usage.md](docs/usage.md) | Установка, CLI, трей, автозапуск, проблемы |
| [docs/architecture.md](docs/architecture.md) | Архитектура, лестница состояний, модули |
| [docs/configuration.md](docs/configuration.md) | Справочник `config.yaml` |
| [docs/throne.md](docs/throne.md) | Обход Throne / `SO_BINDTODEVICE` |

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp config.example.yaml config.yaml   # поправьте iface/gateway при необходимости

argus-netmon --once -v   # разовая проверка
argus-netmon -v          # трей
```

Конфиг: `./config.yaml` или `~/.config/argus-netmon/config.yaml`.

## Состояния

```text
NO_LAN → DOWN → WHITELIST → RU_ZONE → OK (или DEGRADED)
```

- **WHITELIST** — только allow‑list (госуслуги, ya.ru, …)
- **RU_ZONE** — шире (esad7.ru, pikabu.ru), иностранное закрыто
- **OK** — github / wikipedia / example.com и т.п.

Подробнее: [docs/architecture.md](docs/architecture.md).

## Throne

Нужен реальный канал модема, не VPN. Обычно достаточно `use_bind_device: true`.  
См. [docs/throne.md](docs/throne.md).

> **Только на стадии разработки:** правило `processName:python3.10` → Direct затрагивает *все* процессы на этом интерпретаторе. Основной обход — bind; после сборки бинаря используйте `processName:argus-netmon`.

## Стек

Python 3.10+, pystray, Pillow, PyYAML; уведомления через `notify-send`.
