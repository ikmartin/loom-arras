// An agent document written from scratch (`loom draft --ai NAME --new`) waits in Incoming until the author starts a working document from it, every id it defines made plain.
import {expect, test} from '../served';
import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

test.use({
 prepareQuilt: async ({}, use) => {
  await use(({root, loom}) => {
   loom(['draft','--ai','survey','--new']);
   const draft = join(root,'drafting-ai/survey.tex');
   writeFileSync(draft, readFileSync(draft,'utf8').replace('\\begin{document}\n', '\\begin{document}\n\\begin{remark}\\label{sy-0C00-ai}\nA survey remark.\n\\end{remark}\n'));
  });
 }
});

test('Incoming starts a working document from an agent document written from scratch', async ({page, served}) => {
 await page.goto('/review/incoming');
 await page.getByLabel('Contribution').selectOption('drafting-ai/survey.tex');
 const form = page.getByTestId('start-contribution');
 const field = form.getByLabel('New working document');
 await expect(field).toHaveValue('drafting/survey-1.tex');
 await field.fill('drafting/survey-notes.tex');
 await form.getByRole('button', {name: 'Start a working document from it'}).click();
 const notice = page.getByRole('status').filter({hasText: 'Started'});
 await expect(notice).toContainText('Started survey-notes.tex from the agent document');
 expect(readFileSync(join(served.root,'drafting/survey-notes.tex'),'utf8')).toContain('\\label{sy-0C00}');
 // started, it leaves Incoming, and the new document is listed with the person's own
 await expect(page.getByTestId('start-contribution')).toHaveCount(0);
 await notice.getByRole('link', {name: 'survey-notes.tex'}).click();
 await expect(page.locator('main')).toContainText('A survey remark');
 await expect(page.getByTestId('docs-drafts')).toContainText('survey-notes.tex');
});
