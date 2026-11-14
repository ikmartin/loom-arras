// The person's open tab: node holder.mjs URL MINUTES; then write $S/holder/cmd-N.json = [[op,arg],...] and read $S/holder/out-N.txt
import { chromium } from '/Users/isaac/dev/loom-arras/arras/node_modules/playwright/index.mjs';
import fs from 'fs';
const [url, minutes] = process.argv.slice(2);
const dir = process.env.HOLDER_DIR;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
const end = Date.now() + (+minutes) * 60000;
let n = 1;
fs.writeFileSync(`${dir}/ready`, 'ok');
while (Date.now() < end) {
  const f = `${dir}/cmd-${n}.json`;
  if (!fs.existsSync(f)) { await page.waitForTimeout(500); continue; }
  let out = '';
  const steps = JSON.parse(fs.readFileSync(f, 'utf8'));
  for (const [op, arg] of steps) {
    try {
      if (op === 'goto') { await page.goto(arg, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500); out += `goto ${page.url()}\n`; }
      else if (op === 'click') { await page.getByText(arg, { exact: true }).first().click(); out += `clicked ${arg}\n`; }
      else if (op === 'clicksel') { await page.locator(arg).first().click(); out += `clicked ${arg}\n`; }
      else if (op === 'wait') await page.waitForTimeout(+arg);
      else if (op === 'shot') { await page.screenshot({ path: arg }); out += `shot ${arg}\n`; }
      else if (op === 'fullshot') { await page.screenshot({ path: arg, fullPage: true }); out += `shot ${arg}\n`; }
      else if (op === 'text') out += 'TEXT: ' + (await page.innerText('body')).slice(0, +(process.env.TEXTMAX || 4000)) + '\n';
      else if (op === 'eval') out += 'EVAL: ' + JSON.stringify(await page.evaluate(arg)) + '\n';
      else if (op === 'select') {
        // select the phrase arg inside the main reading pane by dragging the mouse over it
        const box = await page.evaluate((phrase) => {
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = w.nextNode())) {
            const i = node.textContent.indexOf(phrase);
            if (i >= 0 && node.parentElement.closest('main, article, .fragment, [data-src]')) {
              node.parentElement.scrollIntoView({ block: 'center' });
              const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + phrase.length);
              const rs = r.getClientRects(); const a = rs[0], b = rs[rs.length - 1];
              return { x1: a.left + 1, y1: a.top + a.height / 2, x2: b.right - 1, y2: b.top + b.height / 2 };
            }
          }
          return null;
        }, arg);
        if (!box) { out += `phrase not found: ${arg}\n`; continue; }
        await page.waitForTimeout(500);
        const box2 = await page.evaluate((phrase) => {
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let node;
          while ((node = w.nextNode())) { const i = node.textContent.indexOf(phrase);
            if (i >= 0 && node.parentElement.closest('main, article, .fragment, [data-src]')) {
              const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + phrase.length);
              const rs = r.getClientRects(); const a = rs[0], b = rs[rs.length - 1];
              return { x1: a.left + 1, y1: a.top + a.height / 2, x2: b.right - 1, y2: b.top + b.height / 2 }; } }
          return null; }, arg);
        await page.mouse.move(box2.x1, box2.y1); await page.mouse.down(); await page.mouse.move(box2.x2, box2.y2, { steps: 8 }); await page.mouse.up();
        await page.waitForTimeout(800);
        out += 'selected: ' + JSON.stringify(await page.evaluate(() => String(window.getSelection()))) + '\n';
      }
    } catch (e) { out += `FAILED ${op} ${arg}: ${String(e).slice(0, 300)}\n`; }
  }
  out += 'console errors: ' + errs.splice(0).slice(0, 5).join(' | ') + '\n';
  fs.writeFileSync(`${dir}/out-${n}.txt`, out);
  n++;
}
await browser.close();
