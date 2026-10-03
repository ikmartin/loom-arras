import {expect, test} from '../served';
import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

for (const width of [736, 1100, 1440]) {
 test(`section source, preamble and close/reopen at ${width}px`, async ({page, served}) => {
  await page.setViewportSize({width, height:1000});
  const sourcePath = 'drafting/sections-test.tex';
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
  writeFileSync(join(served.root,sourcePath),text);
  served.loom(['draft',sourcePath,'--ai','first-scope','--section','sy-0A00']);
  served.loom(['draft',sourcePath,'--ai','second-scope','--section','sy-0B00']);
  const draft = join(served.root,'drafting-ai/first-scope.tex');
  writeFileSync(draft,readFileSync(draft,'utf8').replace('Original','Proposed').replace('First prose.','New prose.').replace('\\begin{document}','\\newcommand{\\extra}{E}\n\\begin{document}'));
  await page.goto('/review?show=incoming');
  await expect(page.getByLabel('Contribution')).toContainText('first-scope');
  await page.getByLabel('Contribution').selectOption('drafting-ai/first-scope.tex');
  const row = page.getByTestId('adoption-sy-0A01');
  const use = row.getByRole('button',{name:'Use proposed version',exact:true});
  // The watcher may publish an intermediate draft while the fixture is still being written. Inspect the final proposal before selecting it (V3).
  await expect(row).toContainText('Proposed');
  await expect(page.getByRole('button',{name:'Preamble changes Not selected',exact:true})).toBeVisible();
  await expect(row.locator('mjx-container').first()).toBeVisible();
  const math = await row.locator('mjx-container').first().elementHandle();
  const poll = page.waitForResponse(r => r.url().endsWith('/build/manifest.json') && r.status() === 200);
  const [decision] = await Promise.all([
   page.waitForResponse(r => r.url().endsWith('/_api/adopt-decision')),
   use.click()
  ]);
  expect(decision.ok(), await decision.text()).toBe(true);
  await expect(use).toHaveAttribute('aria-pressed','true');
  await poll;
  expect(await math!.evaluate(node => node.isConnected)).toBe(true);
  await row.getByRole('button',{name:'Leave out for now',exact:true}).click();
  await expect(use).toHaveAttribute('aria-pressed','false');
  await use.click();
  await expect(use).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button',{name:'Preamble changes Not selected',exact:true}).click();
  await expect(page.getByLabel('Include preamble changes')).not.toBeChecked();
  await page.getByLabel('Include preamble changes').check();
  await page.getByRole('button',{name:'Preview selected changes',exact:true}).click();
  await expect(page.getByTestId('adoption-preview')).toContainText('Mathematics affected');
  await expect(page.getByTestId('adoption-preview')).toContainText('Preamble changes included');
  await page.getByRole('button',{name:'Incorporate selected changes',exact:true}).click();
  await expect.poll(() => readFileSync(join(served.root,sourcePath),'utf8')).toContain('Proposed');
  const applied = readFileSync(join(served.root,sourcePath),'utf8');
  expect(applied).toContain('First prose.');
  expect(applied).toContain('Second prose.');
  expect(applied).toContain('\\newcommand{\\extra}');
  await page.goto('/master/first-scope');
  await page.getByRole('button',{name:'Close draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Close and keep saved copy'})).toBeVisible();
  await page.getByRole('button',{name:'Close and keep saved copy'}).click();
  await expect(page.locator('main')).toContainText('Closed agent document');
  await page.getByRole('button',{name:'Reopen draft'}).click();
  await expect(page.getByRole('button',{name:'Close draft',exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
 });
}
