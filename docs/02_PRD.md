# PRD: пользовательские сценарии

## Команды admin Telegram
- `/start`: доступ только owner Telegram ID из `FACTORY_ADMIN_USER_IDS`; прочим отказ без утечки файлов.
- `/mode_a 10`: создать партию из ровно 10 независимых слотов (не >10 автоматом), берёт пары из approved/manual prepared library.
- `/mode_b 10`: зарезервировать 10 уникальных комбинаций только approved assets; при нехватке доступны меньше с явным отчётом.
- `/status`: прогресс партий, pending review, errors и денежные затраты (где известны).
- `/help`: краткие инструкции.
- Для каждой тройки original/reference/result Telegram album с текстом case id и кнопками `✅ Принять`, `🔁 Переделать`, `❌ Отказ`; логика callback idempotent: двойное нажатие не должно генерировать дубль.
- Для финальных видео: превью+оригинальный файл (`sendDocument`, если нужен сохранённый master) и кнопки `✅ Одобрить`, `♻️ Пересобрать`, `❌ Отклонить`. Публикация вне продукта.

## A: processing / approval
- Предварительно 50 пар фото, хранящихся как независимые original+reference files с pair_id, source/rights metadata.
- Worker выполняет текущий Analyzer → Generator → Validator. Factory только принимает готовый результат от Worker, не повторяет provider API.
- После возврата `COMPLETED` у Worker результат идёт в staging и `PENDING_REVIEW`, **не** в approved library. APPROVE => immutability snapshot, `APPROVED` и `SCREENCAST_QUEUED` + монтаж. Retry создаёт новую attempt с новым idempotency UUID, old failed file в staging, budget guard, max retries default 3. REJECT_FINAL — слот окончательно закрыт.
- При approve не ждать решения по другим 9. На завершении `PARTIAL` если окончательно отклонены/невосстановимы некоторые слоты.
- Новые анимации аватаров через Kling/референсы motion либо reuse при выставленном разрешении; для быстрого MVP production works in test with preexisting avatar MP4, а Kling module должен поддерживать подстановку реального провайдера позже.

## B: recombination
- Только approved case screencast + approved animation + compatible tagged hook; fresh exact combo transactionally reserved; prefer unused avatar/screencast pairs; keep statuses reserved/failed/rendered/approved/rejected. Failed may be rerendered **same work order** rather than create another duplicate row.
- No generation API and no auto variants. Cost = incremental local rendering (electricity) and no AI calls, excluding past asset costs.

## Captions/montage
- Hook 0–3s, Telegram scene with instruction overlays tied to event IDs, CTA 2–3s, final montage to ~30s. Text initially chosen from tagged templates, generated automatically; no manual typing.
- Result original/reference/processing/result time events produce captions; avoid overlay onto important Telegram UI or unsafe platform margins.
- Output H.264/AAC-compatible MP4 (audio optional/empty), 1080x1920 30 fps; user selects music at upload.
- Remotion screenshot remains visual source of truth; avoid new intro; maintain passed v9 viewport fill.

## Reliability
- SQLite durable queue states & idempotent callbacks, restart recovery. Limit 1 local heavy render at once (Remotion concurrency=1 starting point). AI concurrency limited by Worker/provider quotas.
- Provider failure/reconciliation leaves explicit status and never silently spends on retries.
- Technical validators on final MP4: ffprobe width/height/fps/duration/codecs, artifact existence, no zero-size, timestamps; no AI aesthetic QA.
- Cost event on each generation attempt including failures; actual vs estimated vs unknown tracked.
