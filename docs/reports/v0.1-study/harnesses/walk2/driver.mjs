// Long-lived Playwright driver: one headless Chromium page that persists between commands.
// Start:  node driver.mjs [port=48199] [shotsDir=./shots]
// Send:   ./d.sh '{"cmd":"click","x":100,"y":200,"shot":"name"}'   (or an array of such objects, run in order)
// See DRIVER.md for the command list.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire('/Users/isaac/dev/loom-arras/arras/node_modules/');
const { chromium } = require('playwright');

const PORT = Number(process.argv[2] || 48199);
const HERE = path.dirname(new URL(import.meta.url).pathname);
const SHOTS = path.resolve(process.argv[3] || path.join(HERE, 'shots'));
fs.mkdirSync(SHOTS, { recursive: true });
const LOG = path.join(HERE, 'driver-events.log');
const ev = (s) => fs.appendFileSync(LOG, `${new Date().toISOString()} ${s}\n`);

const browser = await chromium.launch({ headless: true });
let context = await browser.newContext({ viewport: { width: Number(process.env.W || 1440), height: Number(process.env.H || 900) }, acceptDownloads: true });
await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'http://127.0.0.1:48150' }).catch(() => {});
const pages = [];
let current = null;
let pendingDialog = null;
const downloads = [];

function watch(p) {
  pages.push(p);
  p.on('console', (m) => { if (['error', 'warning'].includes(m.type())) ev(`console.${m.type()} [${p.url()}] ${m.text()}`); });
  p.on('pageerror', (e) => ev(`pageerror [${p.url()}] ${e.message}`));
  p.on('dialog', (d) => { pendingDialog = d; ev(`dialog ${d.type()}: ${d.message()}`); });
  p.on('download', async (d) => { const f = path.join(SHOTS, '..', 'downloads', d.suggestedFilename()); fs.mkdirSync(path.dirname(f), { recursive: true }); await d.saveAs(f).catch(() => {}); downloads.push(f); ev(`download ${d.suggestedFilename()} -> ${f}`); });
  p.on('requestfailed', (r) => ev(`requestfailed ${r.url()} ${r.failure()?.errorText}`));
  p.on('response', (r) => { if (r.status() >= 400) ev(`http ${r.status()} ${r.url()}`); });
  p.on('close', () => { const i = pages.indexOf(p); if (i >= 0) pages.splice(i, 1); if (current === p) current = pages[pages.length - 1] || null; });
}
const onPage = (p) => { ev(`new page opened: ${p.url()}`); if (!pages.includes(p)) watch(p); };
context.on('page', onPage);
current = await context.newPage();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function shot(name, full = false) {
  const f = path.join(SHOTS, `${name}.png`);
  await current.screenshot({ path: f, fullPage: !!full });
  return f;
}

function visibleText(text, exact, nth) {
  let loc = current.getByText(text, { exact: !!exact });
  return loc.filter({ visible: true }).nth(nth || 0);
}

async function titleAt(x, y) {
  return current.evaluate(([x, y]) => {
    let el = document.elementFromPoint(x, y);
    const tag = el ? el.tagName.toLowerCase() : null;
    while (el && !el.getAttribute?.('title')) el = el.parentElement;
    return { tooltip: el ? el.getAttribute('title') : null, element: tag };
  }, [x, y]);
}

async function run(c) {
  const out = {};
  switch (c.cmd) {
    case 'goto': await current.goto(c.url, { waitUntil: 'domcontentloaded' }); await sleep(c.wait ?? 1500); break;
    case 'reload': await current.reload({ waitUntil: 'domcontentloaded' }); await sleep(c.wait ?? 1500); break;
    case 'back': await current.goBack(); await sleep(c.wait ?? 800); break;
    case 'click': await current.mouse.click(c.x, c.y, { button: c.button || 'left', clickCount: c.count || 1, modifiers: c.modifiers }); break;
    case 'dblclick': await current.mouse.dblclick(c.x, c.y); break;
    case 'clickText': { const l = visibleText(c.text, c.exact, c.nth); const b = await l.boundingBox({ timeout: 3000 }); await l.click({ timeout: 3000, button: c.button || 'left' }); out.at = b && { x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2) }; break; }
    case 'hover': await current.mouse.move(c.x, c.y, { steps: 4 }); await sleep(c.wait ?? 700); Object.assign(out, await titleAt(c.x, c.y)); break;
    case 'hoverText': { const l = visibleText(c.text, c.exact, c.nth); await l.hover({ timeout: 3000 }); const b = await l.boundingBox(); await sleep(c.wait ?? 700); Object.assign(out, await titleAt(b.x + b.width / 2, b.y + b.height / 2)); break; }
    case 'type': await current.keyboard.type(c.text, { delay: c.delay ?? 20 }); break;
    case 'press': await current.keyboard.press(c.key); break;
    case 'drag': { // select text or drag things: from (x1,y1) to (x2,y2)
      await current.mouse.move(c.x1, c.y1); await current.mouse.down();
      await current.mouse.move(c.x2, c.y2, { steps: c.steps || 12 }); await sleep(150); await current.mouse.up(); break; }
    case 'scroll': await current.mouse.move(c.x ?? 720, c.y ?? 450); await current.mouse.wheel(c.dx || 0, c.dy || 0); break;
    case 'dropFile': { // simulate dragging a file from the desktop onto (x,y)
      const buf = fs.readFileSync(c.path).toString('base64');
      out.result = await current.evaluate(async ([b64, name, mime, x, y, hoverOnly]) => {
        const bin = Uint8Array.from(atob(b64), (ch) => ch.charCodeAt(0));
        const file = new File([bin], name, { type: mime });
        const dt = new DataTransfer(); dt.items.add(file);
        const target = document.elementFromPoint(x, y) || document.body;
        const opts = { bubbles: true, cancelable: true, composed: true, dataTransfer: dt, clientX: x, clientY: y };
        target.dispatchEvent(new DragEvent('dragenter', opts));
        target.dispatchEvent(new DragEvent('dragover', opts));
        if (hoverOnly) return `hovering over ${target.tagName}`;
        await new Promise((r) => setTimeout(r, 300));
        const t2 = document.elementFromPoint(x, y) || document.body;
        t2.dispatchEvent(new DragEvent('dragover', opts));
        t2.dispatchEvent(new DragEvent('drop', opts));
        return `dropped on ${t2.tagName}`;
      }, [buf, path.basename(c.path), c.mime || 'application/pdf', c.x, c.y, !!c.hoverOnly]);
      break; }
    case 'paste': { // put text on the clipboard and paste it where the focus is (or dispatch a paste event at x,y)
      out.result = await current.evaluate(async ([text, x, y]) => {
        const target = (x != null ? document.elementFromPoint(x, y) : document.activeElement) || document.body;
        const dt = new DataTransfer(); dt.setData('text/plain', text);
        const e = new ClipboardEvent('paste', { bubbles: true, cancelable: true, composed: true, clipboardData: dt });
        const notCancelled = target.dispatchEvent(e);
        if (notCancelled && (target.isContentEditable || ['INPUT', 'TEXTAREA'].includes(target.tagName))) document.execCommand('insertText', false, text);
        return `paste dispatched on ${target.tagName}${notCancelled ? '' : ' (handled by page)'}`;
      }, [c.text, c.x ?? null, c.y ?? null]);
      break; }
    case 'resize': await current.setViewportSize({ width: c.width, height: c.height || 900 }); await sleep(500); break;
    case 'shot': break;
    case 'text': { // visible text of the page (what a person could read), optionally of the region under (x,y)
      out.text = await current.evaluate(([x, y]) => {
        let el = x != null ? document.elementFromPoint(x, y) : document.body;
        return el ? el.innerText : '';
      }, [c.x ?? null, c.y ?? null]);
      if (c.max) out.text = out.text.slice(0, c.max);
      break; }
    case 'find': { // where on screen is this visible text?
      const l = current.getByText(c.text, { exact: !!c.exact }).filter({ visible: true });
      const n = await l.count(); out.matches = [];
      for (let i = 0; i < Math.min(n, 12); i++) { const b = await l.nth(i).boundingBox(); if (b) out.matches.push({ i, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2), w: Math.round(b.width), h: Math.round(b.height), text: (await l.nth(i).innerText()).slice(0, 80) }); }
      break; }
    case 'selection': out.selection = await current.evaluate(() => String(window.getSelection())); break;
    case 'dialog': if (pendingDialog) { out.message = pendingDialog.message(); if (c.accept) await pendingDialog.accept(c.text); else await pendingDialog.dismiss(); pendingDialog = null; } else out.message = 'no dialog'; break;
    case 'pages': out.pages = pages.map((p, i) => ({ i, url: p.url(), current: p === current })); break;
    case 'switch': current = pages[c.i]; await current.bringToFront(); break;
    case 'closePage': { const p = pages[c.i]; await p.close(); break; }
    case 'url': break;
    case 'downloads': out.downloads = downloads; break;
    case 'wait': await sleep(c.ms || 1000); break;
    case 'fresh': { // a brand-new browser profile (no stored UI state), like a first visit; keeps the current viewport
      const vp = current ? current.viewportSize() : { width: 1440, height: 900 };
      await context.close(); pages.length = 0;
      context = await browser.newContext({ viewport: c.width ? { width: c.width, height: c.height || 900 } : vp, acceptDownloads: true });
      context.on('page', onPage); current = await context.newPage(); if (!pages.includes(current)) watch(current);
      if (c.url) { await current.goto(c.url, { waitUntil: 'domcontentloaded' }); await sleep(c.wait ?? 2000); }
      break; }
    case 'quit': setTimeout(async () => { await browser.close(); server.close(); process.exit(0); }, 100); out.bye = true; break;
    default: throw new Error(`unknown cmd ${c.cmd}`);
  }
  if (c.cmd !== 'quit' && c.cmd !== 'wait') {
    if (c.after) await sleep(c.after);
    if (c.shot) out.shot = await shot(c.shot, c.full);
    out.url = current?.url();
    if (pendingDialog) out.dialog = pendingDialog.message();
  }
  return out;
}

if (!pages.includes(current)) watch(current);
const server = http.createServer(async (req, res) => {
  let body = '';
  req.on('data', (d) => (body += d));
  req.on('end', async () => {
    let cmds;
    try { cmds = JSON.parse(body); } catch (e) { res.end(JSON.stringify({ error: 'bad json' })); return; }
    const list = Array.isArray(cmds) ? cmds : [cmds];
    const results = [];
    for (const c of list) {
      try { ev(`cmd ${JSON.stringify(c)}`); results.push(await run(c)); }
      catch (e) { results.push({ error: String(e.message || e).split('\n')[0] }); break; }
    }
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify(results.length === 1 ? results[0] : results, null, 1));
  });
});
server.listen(PORT, '127.0.0.1', () => ev(`driver listening on ${PORT}`));
