// Generated from cases/CASE_001.json – edit JSON instead.
export const videoConfig={
  "case_id": "CASE_001",
  "photos": {
    "original": "assets/original.jpg",
    "reference": "assets/reference.jpg",
    "result": "assets/result.png"
  },
  "template": "telegram_full",
  "duration": 30,
  "fps": 30,
  "show_start_screen": false,
  "show_gallery": true,
  "show_fullscreen_result": true,
  "show_bot_profile": true,
  "bot": {
    "name": "Vibe Copy",
    "username": "@vibecopy_bot",
    "description": "Перенесу понравившуюся тебе обработку с любого фото на твоё фото",
    "avatar": "assets/bot-avatar.png"
  },
  "result_file": {
    "name": "result.png",
    "size": "1,7 МБ"
  },
  "gallery_extras": [
    "assets/gallery-1.jpg",
    "assets/gallery-2.jpg",
    "assets/gallery-3.jpg",
    "assets/gallery-4.jpg",
    "assets/gallery-5.jpg",
    "assets/gallery-6.jpg",
    "assets/gallery-7.jpg",
    "assets/gallery-8.jpg",
    "assets/gallery-9.jpg",
    "assets/gallery-10.jpg",
    "assets/gallery-11.jpg",
    "assets/gallery-12.jpg"
  ],
  "messages": {
    "welcome": "Привет! Я Vibe Copy 👋\n\nЯ бот, который с помощью ИИ переносит обработку с одного фото на другое ✨\n\nЛучше всего я работаю с портретами, селфи и lifestyle-фото для соцсетей 📸\n\nДля лучшего результата выбирай референс, похожий на твоё фото по ракурсу и композиции: селфи к селфи, портрет к портрету, крупный план к крупному плану.\n\nВажно: я переношу именно стиль обработки. Я не меняю лицо, позу, фон, одежду и внешность.\n\nУ тебя есть 1 пробная обработка 🎁\n\nОтправь своё фото, которое хочешь обработать.",
    "original_received": "Фото получил 👍\n\nТеперь отправь референс — картинку со стилем обработки, который тебе нравится.",
    "reference_received": "Принял референс.\n\nСейчас перенесу цвет, свет и атмосферу на твоё фото.\n\nПришлю готовый результат в стиле референса.",
    "processing_first": "✨ Обрабатываю фото\n\nСравниваю исходное фото и референс...",
    "processing_second": "✨ Обрабатываю фото\n\nГенерирую результат, обычно это занимает около двух минут.",
    "ready": "Готово ✨\n\nПомоги улучшить Vibe Copy — оцени результат реакцией."
  },
  "buttons": [
    "👍 Нравится",
    "👤 Изменилось лицо",
    "➕ Добавлены лишние объекты",
    "➖ Удалены нужные объекты",
    "Обработать ещё"
  ],
  "cta": {
    "zoom": 1.035,
    "pause_seconds": 1.8
  },
  "ui": {
    "theme": "telegram-light",
    "wallpaper": "assets/telegram-wallpaper.png",
    "phone_time": "15:36",
    "battery_percent": 92,
    "network": "LTE",
    "gallery_scroll_pixels": 0,
    "gallery_background_blur": 6,
    "gallery_bottom_mode": "adaptive",
    "viewer_transition": "shared",
    "gallery_camera_tile": true,
    "photo_max_width": 400,
    "photo_max_height": 535,
    "video_layout": "social_fill_1080x1920",
    "show_status_bar": false,
    "social_fill_mode": "adaptive_reflow"
  },
  "times": {
    "messages": {
      "start": "15:30",
      "welcome": "15:32",
      "original": "15:36",
      "original_ack": "15:36",
      "reference": "15:37",
      "reference_ack": "15:37",
      "processing": "15:37",
      "result": "15:40",
      "ready": "15:40"
    },
    "phone": {
      "start": "15:30",
      "welcome": "15:30",
      "galleryOriginal": "15:36",
      "original": "15:36",
      "galleryReference": "15:37",
      "reference": "15:37",
      "processing": "15:37",
      "result": "15:40",
      "viewer": "15:40",
      "profile": "15:40"
    },
    "mode": "staged",
    "continuous_time": "15:40"
  }
};
