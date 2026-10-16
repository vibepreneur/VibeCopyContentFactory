# Исправление экспорта MP4 на Windows (v6)

## Ошибки

1. `"C:\\Program" не является командой` — в прежнем `tools/render-case.mjs` использовался `shell:true`, из-за чего путь к Node.js в `C:\\Program Files` разделялся на части.
2. `FFmpeg quit with code 3221225477` (`0xC0000005`) — аварийное завершение кодировщика. По логу все 960 кадров были отрисованы, но экспорт оборвался при кодировании.

## Решение

В исправленном скрипте процессы запускаются без `shell`, а для Remotion используется безопасный экспорт:

- `--concurrency=1`
- `--disallow-parallel-encoding`
- H.264

В терминале папки проекта:

```bash
npm run render
```

Готовое видео: `out/CASE_001-phone.mp4`.

Для подробного журнала:

```bash
npm run render -- --verbose
```

Для короткого сценария:

```bash
npm run render -- cases/CASE_SHORT.json
```

Если ошибка FFmpeg повторится, попробуйте отдельно:

```bash
npx remotion render src/index.ts VibeCopyPhone out/test-small.mp4 --codec=h264 --concurrency=1 --disallow-parallel-encoding --scale=0.5 --log=verbose
```

Это диагностика: если уменьшенный экспорт проходит, вероятна зависимость от нагрузки или размера кадров. Если не проходит — изучите новые строки FFmpeg и журнал защиты Windows; одного кода `0xC0000005` недостаточно для точного вывода.

Документация: https://www.remotion.dev/docs/options/disallow-parallel-encoding
