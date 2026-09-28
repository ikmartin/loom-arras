import { expect, test } from '@playwright/test';
import { serve } from '../manifest';

const row = (key: string, status = 'needs-review') => ({key, status, cause:'earlier-change', pull:'', changed_text:true, local_changed:true, invalidated:false});

test('Review defaults to the named reviewer’s mathematical queue', async ({page}) => {
 await serve(page, m => {m.reviewer={name:'Luisa',source:'local'};m.unresolved=[row('sy-0001')];});
 await page.goto('/review');
 await expect(page.getByText('Reviewing as Luisa')).toBeVisible();
 const tabs=page.getByRole('navigation',{name:'Review views'});
 await expect(tabs.getByRole('link')).toHaveText(['Needs review (1)','Documents','Incoming']);
 await expect(tabs.getByRole('link',{name:'Needs review (1)'})).toHaveAttribute('aria-current','page');
 await expect(page.getByTestId('guided-review')).toBeVisible();
 await expect(page.locator('main table')).toHaveCount(0);
});

test('Documents selects one document and retains state and cause details', async ({page}) => {
 await page.goto('/review?document=drafting%2Fmain.tex');
 await expect(page.locator('#review-sy-0003')).toBeVisible();
 await page.getByLabel('Document',{exact:true}).selectOption('drafting/talk.tex');
 await expect(page.locator('#review-sy-0003')).toHaveCount(0);
 await expect(page.locator('#review-sy-999a')).toBeVisible();
});

test('all causes can be selected without losing the current block', async ({page}) => {
 await serve(page,m=>{m.unresolved=[row('sy-0001')];});
 await page.goto('/review');
 const reason=page.getByLabel('Reason for review');
 expect(await reason.locator('option').count()).toBeGreaterThan(1);
 await expect(reason).toHaveValue('own-text-changed||');
 await reason.selectOption({index:1});
 await expect(page).toHaveURL(/cause=/);
 await expect(page.getByTestId('guided-review').getByRole('heading',{name:'Current statement'})).toBeVisible();
});

test('pending and attention are distinct from an empty review', async ({page}) => {
 await serve(page,m=>{m.unresolved=[row('sy-0001','ok'),row('sy-0002','requires-attention')];});
 await page.goto('/review');
 await expect(page.getByRole('heading',{name:'1 decision ready to record'})).toBeVisible();
 await expect(page.getByText('Requires attention (1)',{exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Nothing needs review'})).toHaveCount(0);
});

test('narrow layouts collapse the queue before stacking the comparison', async ({page}) => {
 await serve(page,m=>{m.unresolved=[row('sy-0001')];});
 await page.setViewportSize({width:1000,height:900});
 await page.goto('/review');
 await expect(page.locator('aside[aria-label="Review queue"] details').first()).not.toHaveAttribute('open');
 const pair=page.getByTestId('guided-review');
 const left=await pair.locator(':scope > section').first().boundingBox();
 const right=await pair.locator(':scope > section').last().boundingBox();
 expect(right!.x).toBeGreaterThan(left!.x);
 expect(Math.abs(right!.y-left!.y)).toBeLessThan(2);
});

test('prose is inspected in Incoming without mathematical acceptance controls', async ({page}) => {
 await serve(page,m=>{m.contributions=[];m.incoming={remote:'origin',branch:'main',base:'a'.repeat(40),commit:'b'.repeat(40),observed:'2026-09-28',files:[{status:'M',path:'drafting/main.tex',diff:'-Old prose\n+New prose'}],changes:[{key:'prose:setup',name:'Introduction',category:'prose',kind:'edited',local_changed:false,conflict:false,already_local:false,current:'Old prose',proposed:'New prose',affected:[]},{key:'sy-0001',kind:'edited',current:'Old definition',proposed:'New definition',local_changed:false,conflict:false,already_local:false,affected:[]}]};});
 await page.goto('/review?show=incoming');
 await expect(page.getByText('Old prose',{exact:true})).toBeVisible();
 await expect(page.getByText('New prose',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Mark OK'})).toHaveCount(0);
 await expect(page.getByTestId('incoming-incorporation')).toContainText('all changes in this pull');
 await page.getByRole('button',{name:'Next change'}).click();
 await expect(page.getByText('New definition',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Previous change'}).click();
 await expect(page.getByText('New prose',{exact:true})).toBeVisible();
});

test('AI proof attribution distinguishes the source from the reviewer', async ({page}) => {
 await serve(page,m=>{m.reviewer={name:'Luisa',source:'local'};m.unresolved=[{...row('sy-0002/proof'),contribution:'drafting-ai/proposal.tex',source_label:'AI revision'}];m.keys['sy-0002/proof'].acceptance.causes=[{kind:'dependency-changed',id:'sy-0002',diff:null}];});
 await page.goto('/review');
 await expect(page.getByText('Existing proof · statement changed in the AI revision')).toBeVisible();
 await expect(page.getByText('Reviewing as Luisa')).toBeVisible();
});

test('Mark OK stays pending until Finish review records acceptance', async ({page}) => {
 let status='needs-review', accepted=false;
 let decision: Record<string,unknown> | undefined;
 await page.route('**/_api',route=>route.fulfill({json:{write_api:1,capabilities:['review-decision','review-finish']}}));
 await page.route('**/_api/review-decision',async route=>{decision=route.request().postDataJSON();status=String(decision!.status);await route.fulfill({json:{ok:true}});});
 await page.route('**/_api/review-finish',async route=>{accepted=true;await route.fulfill({json:{ok:true}});});
 await serve(page,m=>{m.reviewer={name:'Luisa',source:'local'};m.unresolved=accepted?[]:[row('sy-0001',status)];});
 await page.goto('/review');
 await page.getByRole('button',{name:'Mark OK',exact:true}).click();
 await expect(page.getByRole('heading',{name:'1 decision ready to record'})).toBeVisible();
 expect(accepted).toBe(false);
 expect(decision).toMatchObject({key:'sy-0001',status:'ok',reviewer:'Luisa'});
 await page.getByRole('button',{name:'Finish review · 1',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Nothing needs review'})).toBeVisible();
 expect(accepted).toBe(true);
});

test('attention-only review remains accessible without implying completion', async ({page}) => {
 await serve(page,m=>{m.unresolved=[row('sy-0001','requires-attention')];});
 await page.goto('/review');
 await expect(page.getByRole('heading',{name:'1 block still requires attention'})).toBeVisible();
 await page.getByRole('button',{name:'Widget',exact:true}).click();
 await expect(page.getByTestId('guided-review')).toBeVisible();
 await expect(page.getByRole('button',{name:/Finish review/})).toHaveCount(0);
});

test('Incoming accepts only explicitly chosen mathematics while incorporating the whole pull', async ({page}) => {
 let submitted: any = null;
 await serve(page,m=>{m.reviewer={name:'Luisa',source:'local'};m.contributions=[];m.incoming={remote:'origin',branch:'main',base:'a'.repeat(40),commit:'b'.repeat(40),observed:'2026-09-28',files:[],changes:[{key:'prose:intro',name:'Introduction',category:'prose',kind:'edited',current:'Old prose',proposed:'New prose',affected:[]},{key:'sy-0001',name:'Lemma',kind:'edited',current:'Old lemma',proposed:'New lemma',affected:[]}]};});
 await page.route('**/_api',route=>route.fulfill({json:{write_api:1,capabilities:['sync-incorporate','sync-preview'],token:'test'}}));
 const fragment={path:'incorporation-review/example.html',macros:[]};
 await page.route('**/build/incorporation-review/example.html',route=>route.fulfill({contentType:'text/html',body:'<div class="env"><p>Inspected mathematics.</p></div>'}));
 await page.route('**/_api/sync-preview',route=>route.fulfill({json:{ok:true,result:{token:'preview',reviewer:'Luisa',items:[{key:'sy-0001',name:'Lemma',reason:'Statement changed',local:fragment,proposed:fragment,unavailable:''},{key:'sy-0001:proof',name:'Existing proof',reason:'Existing proof · statement changed in this pull',local:fragment,proposed:fragment,unavailable:''}]}}}));
 await page.route('**/_api/sync-incorporate',async route=>{submitted=route.request().postDataJSON();await route.fulfill({json:{ok:true,result:{accepted:['sy-0001'],pending:['sy-0001:proof']}}});});
 await page.goto('/review?show=incoming');
 await expect(page.getByRole('heading',{name:'Introduction',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Accept',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Next change',exact:true}).click();
 await expect(page.getByRole('button',{name:'Accept',exact:true})).toBeEnabled();
 await expect(page.getByRole('button',{name:'Accept',exact:true})).toHaveAttribute('aria-pressed','false');
 await page.getByRole('button',{name:'Accept',exact:true}).click();
 expect(submitted).toBeNull();
 await page.getByRole('button',{name:'Next change',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Existing proof',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Accept',exact:true})).toHaveAttribute('aria-pressed','false');
 await page.getByRole('button',{name:'Keep for review',exact:true}).click();
 await page.getByRole('button',{name:'Incorporate pull & accept 1 block',exact:true}).click();
 expect(submitted.accept).toEqual(['sy-0001']);
 expect(submitted.incoming).toBe('b'.repeat(40));
 expect(submitted.review_token).toBe('preview');
});
