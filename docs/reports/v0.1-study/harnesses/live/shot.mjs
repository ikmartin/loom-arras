// node shot.mjs URL OUT.png [waitMs] [w] [h] -- screenshot a page; prints title, console errors and visible text head
import { chromium } from '/Users/isaac/dev/loom-arras/arras/node_modules/playwright/index.mjs';
const [url, out, wait = '4000', w = '1440', h = '900'] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
const errs = [];
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
const t0 = Date.now();
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(+wait);
await page.screenshot({ path: out });
console.log('loaded+wait ms', Date.now() - t0, 'title:', await page.title());
console.log((await page.innerText('body')).slice(0, 1500));
console.log('console:', errs.slice(0, 10).join('\n'));
await browser.close();
