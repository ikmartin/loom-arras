import { chromium } from '/Users/isaac/dev/loom-arras/arras/node_modules/@playwright/test/index.mjs';
const S = process.argv[2]; // the directory holding page.html
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1360, height: 860 } });
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
await page.goto('file://' + S + '/page.html');
await page.waitForFunction(() => window.MathJax && MathJax.startup && MathJax.startup.promise, null, { timeout: 30000 });
await page.evaluate(() => MathJax.startup.promise);
await page.waitForTimeout(2500);
const r = {};
r.marks = await page.locator('#left mark.hl').count();
r.marksOn = await page.locator('#left mark.hl:not(.off)').count();
r.symdefs = await page.locator('#right [class*="symdef-"]').count();
r.symdefsLeft = await page.locator('#left [class*="symdef-"]').count();
r.mjxErrors = await page.locator('mjx-merror, [data-mjx-error]').count();
await page.screenshot({ path: S + '/shots/s1-run.png' });
// click a highlight: card opens; outside click closes
const m = page.locator('#left mark.hl:not(.off)').first();
await m.click();
r.cardOpen = await page.locator('.anncard').count();
r.cardHasId = await page.locator('.anncard').first().innerText().then(t => /a-\d{4}-/.test(t));
// show in report scrolls right only
const leftBefore = await page.evaluate(() => document.querySelector('#left').scrollTop);
await page.locator('[data-inreport]').first().click();
await page.waitForTimeout(1200);
r.leftScrollUnchanged = leftBefore === await page.evaluate(() => document.querySelector('#left').scrollTop);
r.rightScroll = await page.evaluate(() => document.querySelector('#right').scrollTop);
r.windowScroll = await page.evaluate(() => window.scrollY + document.scrollingElement.scrollTop);
await page.screenshot({ path: S + '/shots/s2-showreport.png' });
await page.mouse.click(700, 60); // banner area, outside
r.cardClosed = (await page.locator('.anncard').count()) === 0;
// hover a symbol
const sym = page.locator('#right [class*="symdef-"]').first();
if (await sym.count()) { await sym.evaluate(el => el.scrollIntoView({ block: 'center' })); await page.waitForTimeout(300); const b = await sym.boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.waitForTimeout(400); r.hoverTarget = await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); return e && (e.closest('[class*="symdef-"]') ? 'symdef' : e.tagName); }, [b.x + b.width / 2, b.y + b.height / 2]); r.hoverShown = await page.locator('#nthover').isVisible(); r.hoverText = (await page.locator('#nthover').innerText()).slice(0, 80); await page.screenshot({ path: S + '/shots/s3-hover.png' }); }
// notation panel
await page.locator('[data-nt]').click(); await page.waitForTimeout(400);
r.panelOpen = await page.locator('#npanel').isVisible();
await page.screenshot({ path: S + '/shots/s4-panel.png' });
await page.mouse.click(300, 400);
r.panelClosed = !(await page.locator('#npanel').isVisible());
// run cycling
await page.locator('[data-step="1"]').click(); await page.waitForTimeout(800);
r.afterNext = await page.locator('#runsel').inputValue();
r.marksOnEarlier = await page.locator('#left mark.hl:not(.off)').count();
await page.screenshot({ path: S + '/shots/s5-earlier.png' });
for (const v of ['node', 'invoke', 'cite', 'notation']) {
  await page.locator(`.tabs [data-v="${v}"]`).click(); await page.waitForTimeout(1500);
  await page.screenshot({ path: `${S}/shots/v-${v}.png`, fullPage: false });
}
await page.locator('.tabs [data-v="cite"]').click(); await page.waitForTimeout(800);
await page.locator('[data-cite="1"]').first().click(); await page.waitForTimeout(1200);
await page.screenshot({ path: S + '/shots/v-cite1.png' });
await page.locator('.tabs [data-v="notation"]').click(); await page.waitForTimeout(1200);
r.notationSyms = await page.locator('#view [class*="symdef-"]').count();
r.mjxErrorsEnd = await page.locator('mjx-merror, [data-mjx-error]').count();
await page.setViewportSize({ width: 400, height: 860 });
await page.locator('.tabs [data-v="run"]').click(); await page.waitForTimeout(1500);
r.hscroll = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
await page.screenshot({ path: S + '/shots/s6-phone.png' });
console.log(JSON.stringify(r, null, 1)); console.log(errors.join('\n'));
await browser.close();
