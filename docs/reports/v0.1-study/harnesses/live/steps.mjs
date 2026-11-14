// node steps.mjs URL step... ; steps: click=TEXT | clicksel=CSS | wait=MS | shot=PATH | text | url | eval=JS | select=TEXT (select words) | goto=URL
import { chromium } from '/Users/isaac/dev/loom-arras/arras/node_modules/playwright/index.mjs';
const [url, ...steps] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);
for (const s of steps) {
  const i = s.indexOf('='); const k = i < 0 ? s : s.slice(0, i); const v = i < 0 ? '' : s.slice(i + 1);
  try {
    if (k === 'click') await page.getByText(v, { exact: true }).first().click();
    else if (k === 'clicksel') await page.locator(v).first().click();
    else if (k === 'wait') await page.waitForTimeout(+v);
    else if (k === 'shot') { await page.screenshot({ path: v }); console.log('shot', v); }
    else if (k === 'text') console.log('TEXT:', (await page.innerText('body')).slice(0, 2500));
    else if (k === 'url') console.log('URL:', page.url());
    else if (k === 'goto') { await page.goto(v, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500); }
    else if (k === 'eval') console.log('EVAL:', JSON.stringify(await page.evaluate(v)));
    else if (k === 'hold') { console.log('holding', v, 'ms'); await page.waitForTimeout(+v); }
  } catch (e) { console.log('STEP FAILED', s, String(e).slice(0, 300)); }
}
console.log('console errors:', errs.slice(0, 8).join(' | '));
await browser.close();
