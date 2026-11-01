# Throne / обход TUN

Монитор должен видеть **мобильную сеть**, а не выход VPN.

## Рекомендуемый способ

В `config.yaml`:

```yaml
bind_device: wlp0s20f3   # ваш Wi‑Fi
use_bind_device: true
```

Работает, когда в Throne выключены **Auto Redirect** и **Strict Route** (иначе `SO_BINDTODEVICE` могут снова заворачивать в core).

Проверка:

```bash
curl --interface wlp0s20f3 -I https://ya.ru/
curl --interface wlp0s20f3 -I https://github.com/
```

## Дополнительно: правило процесса (только разработка)

> Временная мера до бинаря. `processName:python3.10` отправит в Direct **все** процессы на `/usr/bin/python3.10`, не только Argus. Для повседневной работы достаточно `use_bind_device`.

Если всё же нужно на время отладки — Default → Basic → **Direct**:

```text
processName:python3.10
```

или:

```text
processPath:/usr/bin/python3.10
```

Имя сверяйте во вкладке **Connections** (basename от `/proc/self/exe`).  
**После сборки бинаря** замените на узкое правило:

```text
processName:argus-netmon
```

Включите **Enable Tun Routing**, если Direct должен реально уходить «в провод».

### Важно

В TUN‑режиме Direct‑трафик **всё равно виден** в Connections. Смотрите колонку outbound: `direct`, а не «строки нет».

`connection refused` / reset на Direct к иностранным IP при живых ya.ru — типичная картина белых списков, а не поломка правила.

## Диагностика

```bash
argus-netmon --diag
```

Покажет `comm` / `exe`, публичный IP без bind и с bind, выборочные пробы.
