<script lang="ts">
 import { onMount } from 'svelte';
 import { page } from '$app/state';
 import { goto } from '$app/navigation';
 import { store } from '$lib/manifest/client.svelte';
 import { write } from '$lib/write';
 import { displayNode } from '$lib/nodes/display';
 import { keyUrl } from '$lib/nav';
 import Fragment from '$lib/fragments/Fragment.svelte';
 import DiffView from '$lib/components/DiffView.svelte';
 import { causeIdentity, causeLabel } from './evidence';
 import type { UnresolvedReview } from '$lib/manifest/types';
 let { writable }: { writable: boolean } = $props();
 const m = $derived(store.manifest!);
 const rows = $derived(m.unresolved ?? []);
 const todo = $derived(rows.filter(r => r.status === 'needs-review'));
 const ready = $derived(rows.filter(r => r.status === 'ok'));
 const attention = $derived(rows.filter(r => r.status === 'requires-attention'));
 const selected = $derived(page.url.searchParams.has('block') ? page.url.searchParams.get('block')! : todo[0]?.key ?? '');
 const entry = $derived(rows.find(r => r.key === selected));
 const key = $derived(m.keys[selected]);
 const causes = $derived(key?.acceptance?.causes ?? []);
 const cause = $derived(causes.find(c => causeIdentity(c) === page.url.searchParams.get('cause')) ?? causes.find(c => c.kind === 'own-text-changed') ?? causes[0]);
 const comparison = $derived(cause?.comparison);
 let narrow = $state(false);
 let previousReviewer: string | undefined;
 let reviewerInitialized = false;
 let fragmentRoot = $state<HTMLElement|null>(null);
 onMount(() => { const query = matchMedia('(max-width:1100px)'); const update = () => narrow = query.matches; update(); query.addEventListener('change',update); return () => query.removeEventListener('change',update); });
 $effect(() => { const reviewer = m.reviewer?.name; if (reviewerInitialized && reviewer !== previousReviewer) void select(todo[0]?.key??''); previousReviewer = reviewer; reviewerInitialized = true; });
 $effect(() => {
  if (!fragmentRoot) return;
  fragmentRoot.querySelectorAll('.review-citation-target').forEach(e=>e.classList.remove('review-citation-target'));
  const target = cause?.id?.startsWith('equation:') ? `${cause.owner}#${cause.id.slice(9)}` : cause?.id;
  if(target) fragmentRoot.querySelectorAll<HTMLElement>('[data-target]').forEach(e => {if(e.dataset.target === target)e.classList.add('review-citation-target');});
 });
 let busy = $state(false), error = $state(''), notice = $state('');
 const nextKey = () => todo[(todo.findIndex(r=>r.key===selected)+1)%todo.length]?.key ?? '';
 const context = (k: string) => {const n=m.nodes[m.keys[k]?.node??k]; return m.masters.find(d=>d.default && n?.reached_by.includes(d.path))?.path ?? n?.reached_by[0] ?? '';};
 const name = (k: string) => displayNode(m,k,context(k)).name;
 const reason = (k: string) => {const c=m.keys[k]?.acceptance?.causes?.[0]; return c ? causeLabel(m,c) : 'Not yet accepted';};
 async function select(block: string, why = '') {
  const url = new URL(page.url); url.searchParams.set('block',block);
  if (why) url.searchParams.set('cause',why); else url.searchParams.delete('cause');
  await goto(url.pathname + url.search, {noScroll:true,keepFocus:true});
 }
 async function decide(status: UnresolvedReview['status']) {
  if (!entry || busy) return;
  busy=true; error=''; const old = entry.key;
  const answer=await write('review-decision',{key:old,status});
  if(answer.ok){await store.refresh(); const next=store.manifest?.unresolved?.find(r=>r.status==='needs-review' && r.key!==old); await select(next?.key??'');}
  else error=answer.error?.message??'Could not save the decision';
  busy=false;
 }
 async function finish(){
  busy=true;error='';const count=ready.length;
  const answer=await write('review-finish',{});
  if(answer.ok){await store.refresh();notice=`Review recorded for ${m.reviewer?.name}. ${count} pending decision${count===1?'':'s'} completed.`;await select(store.manifest?.unresolved?.find(r=>r.status==='needs-review')?.key??'');}
  else error=answer.error?.message??'Could not finish review'; busy=false;
 }
 function mount(root: HTMLElement){fragmentRoot=root;}
</script>
<div class="review-workspace">
 <aside class="review-queue" aria-label="Review queue">
  <details open={!narrow}><summary>Needs review ({todo.length})</summary>{#each todo as row}<button aria-label={name(row.key)} class:active={selected===row.key} onclick={()=>select(row.key)}>{name(row.key)}<small>{reason(row.key)}</small>{#if row.invalidated}<small>Changed since your decision</small>{/if}</button>{/each}</details>
  {#if ready.length}<details open={!todo.length}><summary>Ready to record ({ready.length})</summary>{#each ready as row}<button aria-label={name(row.key)} class:active={selected===row.key} onclick={()=>select(row.key)}>{name(row.key)}</button>{/each}</details>{/if}
  {#if attention.length}<details open={!todo.length}><summary>Requires attention ({attention.length})</summary>{#each attention as row}<button aria-label={name(row.key)} class:active={selected===row.key} onclick={()=>select(row.key)}>{name(row.key)}</button>{/each}</details>{/if}
 </aside>
 <section class="reading">
 {#if notice}<p role="status">{notice}</p>{/if}
 {#if error}<p role="alert">{error}</p>{/if}
 {#if m.review_covered?.length}<details class="covered"><summary>{m.review_covered.length} dependent blocks set aside until you finish review</summary>{#each m.review_covered as row}<p>{name(row.key)} · covered by {row.via.map(name).join(', ')}</p>{/each}<p>They return if the upstream decision changes.</p></details>{/if}
 {#if key}
  <header class="itemhead"><div><h2>{name(selected)}</h2>{#if entry?.contribution}<p class="muted">{key.kind==='proof' && cause?.kind==='dependency-changed' && cause.id===key.node?'Existing proof · statement changed in the AI revision':entry.source_label}</p>{/if}</div><a class="open-document" href={keyUrl(m,selected)}>Open in document ↗</a></header>
  <div class="pair" data-testid="guided-review">
   <section class="current"><h3 class="version-label">Current {key.kind==='proof'?'proof':'statement'}</h3>{#if key.review_fragment || m.nodes[key.node]?.fragment}<Fragment path={cause?.kind==='own-text-changed' && comparison ? comparison.current : key.review_fragment ?? m.nodes[key.node].fragment} macroSet={key.review_macros} isolatedMacros={!!key.review_macros} onmounted={mount}/>{/if}</section>
   <section class="evidence"><h3>Why this needs review</h3>
    {#if causes.length>1}<select aria-label="Reason for review" value={cause?causeIdentity(cause):''} onchange={e=>select(selected,e.currentTarget.value)}>{#each causes as c,i}<option value={causeIdentity(c)}>{causeLabel(m,c)} · {i+1} of {causes.length}</option>{/each}</select>{:else if cause}<p>{causeLabel(m,cause)}</p>{:else}<p>{key.acceptance?'No active change to this acceptance.':'No earlier acceptance.'}</p>{/if}
    {#if comparison}<h4>Last accepted by {key.acceptance?.author} · {key.acceptance?.date.slice(0,10)}</h4><Fragment path={comparison.accepted} macroSet={comparison.accepted_macros} isolatedMacros/>{#if cause?.kind!=='own-text-changed'}<h4>Now</h4><Fragment path={comparison.current} macroSet={comparison.current_macros} isolatedMacros={!!comparison.current_macros}/>{/if}
    {:else if cause?.current_fragment}<h4>Current version</h4><Fragment path={cause.current_fragment} macroSet={cause.current_macros} isolatedMacros/>{:else if cause?.diff}<DiffView path={cause.diff}/>{:else if cause?.kind==='dependency-scope-unavailable'}<p>The full display must be identified before this dependency can be verified. Repeated acceptance cannot fix it.</p>{/if}
    <details><summary>Details</summary><p>{key.file}</p>{#if key.acceptances?.length}<p>Accepted by: {key.acceptances.map(a=>`${a.author} · ${a.date.slice(0,10)} · ${a.fresh ? 'Current' : 'Stale'}`).join('; ')}</p>{/if}{#if key.acceptance}<p>Last accepted by {key.acceptance.author} · {key.acceptance.date}</p>{/if}{#if entry?.source_label}<p>Source: {entry.source_label}</p>{/if}{#if cause?.when}<p>First observed {cause.when}</p>{/if}</details>
   </section>
  </div>
  {#if entry}<div class="actions"><div class="actionline">{#if writable}{#if entry.status!=='ok'}<button class="primary" disabled={busy} onclick={()=>decide('ok')}>Mark OK</button>{/if}<button disabled={busy} onclick={()=>decide('requires-attention')}>Requires attention</button>{/if}{#if todo.some(r=>r.key!==selected)}<button class="skip quiet" disabled={busy} onclick={()=>select(nextKey())}>Skip</button>{/if}</div><p class="hint">{entry.status==='ok'?'Ready to record. This block has not yet been accepted.':'Mark OK is recorded as accepted when you finish review.'}</p></div>{/if}
 {:else if ready.length}<h2>{ready.length} decision{ready.length===1?'':'s'} ready to record</h2><p>Your choices are saved. Finish review records their acceptances.</p>{:else if attention.length}<h2>{attention.length} block{attention.length===1?'':'s'} still {attention.length===1?'requires':'require'} attention</h2><p>These blocks have not been accepted.</p>{:else}<h2>Nothing needs review</h2>{/if}
 {#if ready.length && writable}<button class="finish primary" disabled={busy} onclick={finish}>Finish review · {ready.length}</button>{/if}
 {#if !writable}<p class="muted">{m.reviewer?.name?'Review actions require a local write connection.':'Choose your reviewer name in Settings to record decisions.'}</p>{/if}
 </section>
</div>
<style>
 .review-workspace{display:grid;grid-template-columns:185px minmax(0,1fr);min-height:490px;container-type:inline-size}
 aside{padding:22px 12px;border-right:1px solid var(--rule);min-width:0}
 aside details{margin:0 0 20px}
 aside summary{font-size:11px;letter-spacing:.06em;text-transform:uppercase;list-style:none;margin-bottom:12px;color:var(--ink-soft)}
 aside summary::-webkit-details-marker{display:none}
 aside button{display:block;text-align:left;width:100%;border:0;background:transparent;padding:10px;border-radius:4px;margin:3px 0;line-height:1.45;font-size:13px}
 aside button.active{background:var(--review-wash)}
 aside small{display:block;font-size:11px;color:var(--ink-soft);margin-top:4px;line-height:1.5}
 .reading{padding:25px 26px 20px;min-width:0;display:flex;flex-direction:column}
 .itemhead{display:flex;align-items:baseline;justify-content:space-between;gap:18px;margin-bottom:24px}
 h2{font:400 23px/1.25 Georgia,serif;margin:0}
 .itemhead .muted{margin:6px 0 0}
 .open-document{font-size:12px;color:var(--ink-soft);white-space:nowrap;text-decoration:none}
 .open-document:hover{text-decoration:underline;color:var(--review-accent)}
 .pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:26px;flex:1}
 .pair>section{min-width:0;overflow-wrap:break-word}
 .evidence{padding-left:25px;border-left:1px solid var(--rule)}
 h3,h4{font:400 11px/1.5 var(--sans);color:var(--ink-soft);margin:0 0 6px}
 .version-label{margin-bottom:17px}
 h4{margin-top:18px}
 .evidence>p{font-size:13px;margin:0 0 19px}
 .evidence select{width:100%;margin:0 0 18px;font-size:12px}
 details{margin-top:18px;font-size:12px;color:var(--ink-soft)}
 details p{line-height:1.6;overflow-wrap:anywhere}
 .actions{border-top:1px solid var(--rule);padding-top:17px;margin-top:25px}
 .actionline{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
 .skip{margin-left:auto}
 .hint{font-size:11px;color:var(--ink-soft);margin:8px 0 0}
 .finish{margin-top:15px;align-self:flex-end}
 .covered{background:var(--review-wash);padding:10px 12px;border-radius:4px;margin:0 0 18px}
 .muted{font-size:12px;color:var(--ink-soft)}
 .pair :global(.fragment){font-family:Georgia,'Times New Roman',serif;font-size:16px;line-height:1.75;text-align:left}
 .pair :global(.review-citation-target){background:var(--review-wash);border-bottom:1px solid var(--review-accent)}
 .current :global(.review-changed){color:inherit;background:var(--review-add);text-decoration:none;border-bottom:1px solid var(--review-accent)}
 .evidence :global(.review-changed){color:inherit;background:var(--review-remove)}
 @media(max-width:1100px){.review-workspace{grid-template-columns:1fr}aside{display:block;border-right:0;border-bottom:1px solid var(--rule);padding:12px 16px}aside details{margin:0}aside summary{margin:0;cursor:pointer}aside details[open] summary{margin-bottom:8px}aside details[open]{margin-bottom:10px}aside button{width:auto;display:inline-block;vertical-align:top;margin-right:8px}.reading{padding:22px 20px}}
 @media(max-width:560px){.pair{grid-template-columns:1fr}.evidence{border-left:0;border-top:1px solid var(--rule);padding:20px 0 0}.itemhead{flex-wrap:wrap;gap:8px}.reading{padding:20px 16px}}
</style>
