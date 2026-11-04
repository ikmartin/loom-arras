import {expect, test} from '../served';
import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

const sourcePath = 'drafting/sections-test.tex';

test.use({
 prepareQuilt: async ({}, use) => {
  await use(({root, loom}) => {
  const text = String.raw`\documentclass{article}
\usepackage{amsthm}
\newtheorem{lemma}{Lemma}
\begin{document}
\section{First}\label{sy-0A00}
First prose.
\begin{lemma}\label{sy-0A01}Original $x>0$.\end{lemma}
\begin{proof}An unchanged proof.\end{proof}
\section{Second}\label{sy-0B00}
Second prose.
\begin{lemma}\label{sy-0B01}Other statement.\end{lemma}
\end{document}
`;
  writeFileSync(join(root,sourcePath),text);
  loom(['draft',sourcePath,'--ai','first-scope','--section','sy-0A00']);
  loom(['draft',sourcePath,'--ai','second-scope','--section','sy-0B00']);
  const draft = join(root,'.loom/copies/first-scope.tex');
  writeFileSync(draft,readFileSync(draft,'utf8').replace('Original','Proposed').replace('First prose.','New prose.').replace('\\begin{document}','\\newcommand{\\extra}{E}\n\\begin{document}'));
  });
 }
});

for (const width of [736, 1100, 1440]) {
 test(`section source, preamble and close/reopen at ${width}px`, async ({page, served}) => {
  // preview, incorporate, a close that builds the quilt first and a reopen: past the default 30 s on a CI runner
  test.setTimeout(90000);
  await page.setViewportSize({width, height:1000});
  await page.goto('/review/proposed?copy=' + encodeURIComponent('.loom/copies/first-scope.tex'));
  const row = page.locator('[data-testid="change-row"][data-key="sy-0A01"]');
  const preamble = page.locator('[data-testid="change-row"][data-key="preamble"]');
  const shown = page.getByTestId('change-shown');
  // the changes are listed where the counter opens them
  const list = async () => { if (!(await page.getByTestId('change-list').isVisible())) await page.getByTestId('change-at').click(); };
  await list();
  await expect(preamble).toContainText('to decide');
  await row.click();
  await expect(shown).toContainText('Proposed');
  await expect(shown.locator('mjx-container').first()).toBeVisible();
  const [decision] = await Promise.all([
   page.waitForResponse(r => r.url().endsWith('/_api/adopt-decision')),
   page.getByTestId('take-it').click()
  ]);
  expect(decision.ok(), await decision.text()).toBe(true);
  // taking it steps on to the next change to decide, and the next manifest redraws nothing of what is now shown
  await expect(page.getByTestId('change-at')).not.toHaveText(/^1 of /);
  const drawn = await shown.locator('h2').elementHandle();
  await page.waitForResponse(r => r.url().endsWith('/build/manifest.json') && r.status() === 200);
  expect(await drawn!.evaluate(node => node.isConnected)).toBe(true);
  await list();
  await expect(row).toHaveAttribute('data-state','taken');
  await row.click();
  await page.getByTestId('leave-it').click();
  await list();
  await expect(row).toHaveAttribute('data-state','left');
  await row.click();
  await page.getByTestId('take-it').click();
  await list();
  await expect(row).toHaveAttribute('data-state','taken');
  // the preamble is taken the same way as a result, from its row
  await preamble.click();
  await page.getByTestId('take-it').click();
  await list();
  await expect(preamble).toHaveAttribute('data-state','taken');
  await page.keyboard.press('Escape');
  await page.getByTestId('apply').click();
  await expect.poll(() => readFileSync(join(served.root,sourcePath),'utf8')).toContain('Proposed');
  const applied = readFileSync(join(served.root,sourcePath),'utf8');
  expect(applied).toContain('First prose.');
  expect(applied).toContain('Second prose.');
  expect(applied).toContain('\\newcommand{\\extra}');
  await page.goto('/master/.loom/copies/first-scope');
  await page.getByRole('button',{name:'Close draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Close and keep saved copy'})).toBeVisible();
  await page.getByRole('button',{name:'Close and keep saved copy'}).click();
  // closing builds the quilt before it answers, which a CI runner takes longer over
  await expect(page.locator('main')).toContainText('Closed agent document', {timeout: 30000});
  await page.getByRole('button',{name:'Reopen draft'}).click();
  await expect(page.getByRole('button',{name:'Close draft',exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
 });
}
