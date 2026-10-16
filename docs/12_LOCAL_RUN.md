# Локальный запуск Factory (MOCK)

Factory использует существующий Remotion v9, SQLite и локальные файлы. Музыка и публикация остаются ручными. MOCK Worker возвращает технические картинки, а аватар — явно обозначенный тестовый клип; это не результат AI/Kling.

## Установка в PowerShell

Все команды выполняйте из `C:\Проекты\VibeCopyContentFactory`. Глобальные Python-пакеты, настройки Windows и другой проект не изменяются.

```powershell
Set-Location 'C:\Проекты\VibeCopyContentFactory'
python -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
python -X utf8 tools/bootstrap.py ffmpeg
.\.venv\Scripts\python.exe -X utf8 -m factory doctor
```

Зависимости Remotion уже установлены. Только если `Remotion/node_modules` отсутствует, выполните `npm.cmd ci` внутри `Remotion`; не обновляйте версии пакетов автоматически. Portable FFmpeg загружается с gyan.dev, проверяется по опубликованному SHA-256 и распаковывается в `.tools/ffmpeg`. Системный PATH менять не нужно.

Точное проверенное окружение Windows/Python 3.14 зафиксировано в `requirements.lock`; для его повторения используйте этот файл вместо `requirements.txt` в команде pip.

## Демо без секретов

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory demo --verify-remotion
```

Команда создаёт отдельную папку `data/demo/<UUID>`, запускает настоящий localhost HTTP fake Worker, подготавливает 10 пар, два технических клипа и выполняет тестовые решения QA. Режим A демонстрирует 10 кандидатов, немедленный рендер первого одобренного при девяти ожидающих, второй кейс, retry с новым UUID и восемь отказов: итог `PARTIAL`. Режим B собирает 10 уникальных MP4 из одобренного тестового кэша без обращений к Worker. Telegram-доставка имитируется; внешняя сеть и токены не используются.

`--verify-remotion` дополнительно рендерит каждую из двух троек повторно и сравнивает декодированные кадры original/reference/result. Результат: `demo-master.mp4`, `report.json`, `remotion-verification.jpg`, логи и измерения памяти/времени. Тестовые одобрения не заменяют художественную проверку человеком.

Готовые мастеры доступны под понятными именами в `exports/`: два A и десять B. `report.json` перечисляет пути и SHA-256 каждого активного результата. Расходы провайдера `fake` — условные суммы тестовой фикстуры, реальные платные вызовы равны нулю.

На HP рендеры выполняются последовательно и могут занимать заметное время. Текущий прогресс Remotion — в `data/demo/<UUID>/work/<case-id>/remotion.log`. Не запускайте вручную второй Remotion/Studio-рендер одновременно.

После ошибки продолжите ту же демо-базу:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory demo --resume data/demo/UUID --verify-remotion
```

В Codex песочница может запрещать запуск Chromium (`spawn EPERM`). Тогда потребуется разрешить именно локальный рендер вне песочницы. Эта ошибка не требует новой платной попытки: demo продолжает сохранённые задания.

## Обычная локальная библиотека и очередь

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory init
.\.venv\Scripts\python.exe -X utf8 -m factory import-library docs/examples/library-manifest.json
.\.venv\Scripts\python.exe -X utf8 -m factory fake-worker
```

Последнюю команду оставьте работающей. Во втором терминале:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory start a
.\.venv\Scripts\python.exe -X utf8 -m factory run
```

Файл примера манифеста показывает формат; прежде чем импортировать, замените его пути своими файлами **внутри проекта**. Для A нужны 10 подготовленных пар и одобренный клип аватара. Для B — одобренные клипы и скринкасты: они появляются после финального одобрения результатов A. Стандартные пять хуков и один сценарий создаются при инициализации. Клип аватара должен быть читаемым MP4 с видеодорожкой; композитор приводит размер и частоту кадров к выходному формату.

Решения без Telegram, из третьего терминала:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory status
.\.venv\Scripts\python.exe -X utf8 -m factory review case CASE_UUID approve --attempt 1
.\.venv\Scripts\python.exe -X utf8 -m factory review case CASE_UUID retry --attempt 1
.\.venv\Scripts\python.exe -X utf8 -m factory review case CASE_UUID reject-final
.\.venv\Scripts\python.exe -X utf8 -m factory review video VIDEO_UUID approve
.\.venv\Scripts\python.exe -X utf8 -m factory review video VIDEO_UUID remake
.\.venv\Scripts\python.exe -X utf8 -m factory review video VIDEO_UUID reject
.\.venv\Scripts\python.exe -X utf8 -m factory start b
```

Для отдельной демо-базы добавьте `--data data/demo/UUID` **перед** подкомандой. При технической ошибке используйте `resume QUEUE_JOB_UUID`: повторяется то же задание и та же комбинация. Это отличается от `review case ... retry`, который создаёт новый UUID попытки. При `RECONCILIATION_REQUIRED` новая генерация запрещена до сверки предыдущей попытки.

## Отдельный админ-бот

Скопируйте `.env.example` в `.env` локально, заполните `FACTORY_TELEGRAM_TOKEN` отдельного бота и `FACTORY_ADMIN_USER_IDS` (через запятую). Не отправляйте токены в чат. Оставьте `FACTORY_MODE=MOCK`, платные вызовы выключенными; fake Worker должен работать отдельно.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory bot
```

Команда запускает polling, обе очереди и доставку проверок. Отдельный `factory run` тогда не нужен. Пишите боту в личный чат: `/start`, `/mode_a 10`, `/mode_b 10`, `/status`. Реальная Telegram-доставка пока требует отдельного ручного испытания с вашим токеном.

## Проверки и ограничения

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest
```

Проверки контрактов используют настоящий локальный HTTP и fake provider; доменные тесты рендера явно подменяют тяжёлый композитор. Настоящие медиа проверяются отдельной командой `demo --verify-remotion`. Тесты публичного Vibe Copy здесь не запускаются.

Дополнительная независимая проверка готового демо (12 мастеров, timestamps, исходники):

```powershell
.\.venv\Scripts\python.exe -X utf8 tools/verify_artifacts.py data/demo/UUID
```

REAL Mode A намеренно заблокирован до реализации выбранного Kling API и разрешения на расходы. Для реального Worker нужны частный VPN-адрес и отдельный bearer. Реальные Worker/Kling/Telegram, коммерческие права на материалы и production end-to-end не подтверждены. Автопубликации и деплоя нет.
