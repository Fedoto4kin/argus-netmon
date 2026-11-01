# Конфигурация

Ищется в порядке:

1. путь из `-c` / `--config`
2. `$XDG_CONFIG_HOME/argus-netmon/config.yaml`
3. `~/.config/argus-netmon/config.yaml`
4. `./config.yaml` (удобно при разработке)

Образец: [`config.example.yaml`](../config.example.yaml).

После правок конфига **перезапустите** процесс — файл читается только на старте.

## Основные поля

| Поле | Смысл |
|------|--------|
| `lan.interface` / `lan.gateway` | Wi‑Fi iface и IP роутера |
| `lan.ports` | TCP‑порты для проверки шлюза (80/443) |
| `interval_sec` | Пауза между циклами |
| `fail_threshold` / `ok_threshold` | Гистерезис смены состояния |
| `bind_device` / `use_bind_device` | Привязка сокетов к физическому NIC |
| `timeout_sec` | Таймаут одной пробы |
| `probes.whitelist` | Сайты белого списка |
| `probes.domestic` | Ру‑зона вне WL |
| `probes.open` | «Полный» интернет (иностранные) |
| `speed.*` | URL замера, пороги DEGRADED / ~3G |
| `notify.enabled` | Уведомления на смене состояния |
| `autostart.enabled` | Только значение по умолчанию в YAML; факт — XDG desktop |
| `modem.*` | Заготовка под Keenetic RCI |

## Формат пробы

```yaml
- { host: example.com, port: 443, path: /, tls: true, sni: optional.example }
```

Успех: любой HTTP‑ответ `1xx`–`5xx` после успешного TCP(+TLS).  
Для корзины `open` нужна **большинство** успехов (3 хоста → ≥2).  
Для `domestic` из двух хостов — **оба**.  
Для `whitelist` достаточно одного.

## Типичная подстройка под оператора

1. В режиме белых списков отметьте, что открывается, а что нет.
2. WL‑живые → `probes.whitelist` (+ при желании majors вроде ya.ru).
3. Живые только в «ру‑зоне», но не в WL → `probes.domestic`.
4. То, что должно жить только при полном интернете → `probes.open`.
