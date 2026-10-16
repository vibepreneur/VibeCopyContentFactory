import fs from 'node:fs';
import path from 'node:path';

// Выполнять из корневой папки проекта Remotion (где package.json).
const root = process.cwd();
const file = path.join(root, 'src', 'telegram.css');
const backup = path.join(root, 'src', 'telegram.css.bak-v9-3');

if (!fs.existsSync(path.join(root, 'package.json')) || !fs.existsSync(file)) {
  console.error('Ошибка: запустите команду в корневой папке проекта (package.json и src/telegram.css).');
  process.exit(1);
}
const css = fs.readFileSync(file, 'utf8');
const blockPattern = /(\.social-fill\s+\.viewer-social-title\s*\{)([^}]*)(\})/;
const block = css.match(blockPattern);
if (!block) {
  console.error('Не найден CSS-блок .social-fill .viewer-social-title. Файл не изменён.');
  process.exit(1);
}
const radiusPattern = /\bborder-radius\s*:\s*[^;]+;/;
if (!radiusPattern.test(block[2])) {
  console.error('В целевом CSS-блоке нет border-radius. Файл не изменён.');
  process.exit(1);
}
if (/\bborder-radius\s*:\s*999px\s*;/.test(block[2])) {
  console.log('Готово: скругление 999px уже установлено. Изменения не требуются.');
  process.exit(0);
}
const updatedBlock = block[1] + block[2].replace(radiusPattern, 'border-radius:999px;') + block[3];
const updated = css.replace(blockPattern, () => updatedBlock);
if (!fs.existsSync(backup)) fs.copyFileSync(file, backup);
fs.writeFileSync(file, updated, 'utf8');
console.log('Патч v9.3 применён: скругление названия бота = 999px.');
console.log('Резервная копия: src/telegram.css.bak-v9-3');
