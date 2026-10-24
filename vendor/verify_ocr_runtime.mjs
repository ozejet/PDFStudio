// Run with: node vendor/verify_ocr_runtime.mjs
// Tests local language bundles and installed local WASM engine, with no CDN.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const require = createRequire(new URL('../web/package.json', import.meta.url));
const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');
const { createWorker } = require('tesseract.js');
GlobalFonts.registerFromPath(path.join(root, 'vendor/fonts/Sarabun-Regular.ttf'), 'SarabunLocal');

for (const sample of [
  { language: 'eng', text: 'PDF STUDIO 2026', font: 'bold 80px Arial', width: 1100, height: 180, y: 120 },
  { language: 'tha', text: 'ทดสอบ ภาษาไทย', font: '100px SarabunLocal', width: 1500, height: 260, y: 170 },
]) {
  const canvas = createCanvas(sample.width, sample.height);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, sample.width, sample.height);
  ctx.fillStyle = 'black';
  ctx.font = sample.font;
  ctx.fillText(sample.text, 30, sample.y);
  const worker = await createWorker(sample.language, 1, {
    langPath: path.join(root, 'web/public/vendor/ocr/lang'),
    cacheMethod: 'none',
  });
  try {
    await worker.setParameters({ tessedit_pageseg_mode: '6' });
    const { data } = await worker.recognize(canvas.toBuffer('image/png'));
    console.log(JSON.stringify({ language: sample.language, text: data.text.trim(), confidence: data.confidence }));
    if (!data.text.replace(/\s/g, '').includes(sample.text.replace(/\s/g, ''))) {
      throw new Error(`Local ${sample.language} OCR did not recognize the synthetic text`);
    }
  } finally {
    await worker.terminate();
  }
}
