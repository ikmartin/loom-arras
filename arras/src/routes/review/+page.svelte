<script lang="ts">
 import { incomingNotice } from '$lib/review/notice.svelte';
 import '$lib/review/review.css';
 import { onMount } from 'svelte';
 import { page } from '$app/state';
 import { goto } from '$app/navigation';
 import { store } from '$lib/manifest/client.svelte';
 import { can } from '$lib/write';
 import { displayNode } from '$lib/nodes/display';
 import { keyUrl, masterUrl, anchorId } from '$lib/nav';
 import { documentKeys } from '$lib/review/documents';
 import { causeLabel } from '$lib/review/evidence';
 import { reviewFacts,reviewRowBadge } from '$lib/badges';
 import Badge from '$lib/components/Badge.svelte';
 import DiffView from '$lib/components/DiffView.svelte';
 import AdoptionContribution from '$lib/components/AdoptionContribution.svelte';
 import ReviewWorkspace from '$lib/review/ReviewWorkspace.svelte';
 import IncomingPull from '$lib/review/IncomingPull.svelte';
 import type { AdoptionReview } from '$lib/manifest/types';
 const m=$derived(store.manifest!);
 const view=$derived(page.url.searchParams.has('document')?'document':page.url.searchParams.get('show')??'needs-review');
 const reviewed=$derived(m.masters.filter(x=>x.directory!=='drafting-ai'));
 const document=$derived(reviewed.find(x=>x.path===page.url.searchParams.get('document'))??reviewed.find(x=>x.default)??reviewed[0]);
 const rows=$derived(document?documentKeys(m,document.path):[]);
 const adoptions=$derived((m.contributions??[]).filter((x):x is AdoptionReview=>x.kind==='adopt'));
 let source=$state(''),local=$state(false),sync=$state(false),incorporated=$state(''),legacyDismissed=$state(false);
 const selectedSource=$derived(adoptions.some(x=>x.copy===source)?source:m.incoming?'':adoptions[0]?.copy??'');
 const adoption=$derived(adoptions.find(x=>x.copy===selectedSource));
 const todo=$derived((m.unresolved??[]).filter(r=>r.status==='needs-review'));
 onMount(()=>{void can('review-decision').then(x=>local=x);void can('sync-incorporate').then(x=>sync=x);});
</script>
<main class="page review-page">
 <header class="heading"><h1>Review</h1><span>{m.corpus.root_label || m.corpus.name}</span></header>
 {#if m.legacy_review_decisions&&!legacyDismissed}<p>Earlier pending decisions have no reviewer. Review them again under your name. <button onclick={()=>legacyDismissed=true}>Dismiss</button></p>{/if}
 {#if incomingNotice.text}<p role="status">{incomingNotice.text}</p>{/if}
<div class="review-card"><nav class="review-tabs" aria-label="Review views"><a aria-current={view==='needs-review'?'page':undefined} class:active={view==='needs-review'} href="?show=needs-review">Needs review{todo.length?` (${todo.length})`:''}</a><a aria-current={view==='document'?'page':undefined} class:active={view==='document'} href={document?`?document=${encodeURIComponent(document.path)}`:'?show=document'}>Documents</a><a aria-current={view==='incoming'?'page':undefined} class:active={view==='incoming'} href="?show=incoming">Incoming</a><span class="reviewer">{m.reviewer?.name?`Reviewing as ${m.reviewer.name}`:'Choose your reviewer name in Settings'}</span></nav>
 {#if view==='incoming'}
  {#if incorporated}<p role="status">{#if !incomingNotice.text}Changes incorporated. {/if}<a href="?show=needs-review">Review affected mathematics</a>{#if incorporated!=='pull'} · <a href={masterUrl(incorporated)}>Original AI draft and annotations</a>{/if}</p>{/if}
  {#if adoptions.length+(m.incoming?1:0)>1}<label>Contribution <select value={selectedSource} onchange={e=>source=e.currentTarget.value}>{#if m.incoming}<option value="">Fetched pull</option>{/if}{#each adoptions as a}<option value={a.copy}>{a.label}</option>{/each}</select></label>{/if}
  {#if adoption}{#key adoption.copy}<AdoptionContribution contribution={adoption} onincorporated={copy=>incorporated=copy}/>{/key}{:else if m.incoming}{#key m.incoming.commit}<IncomingPull incoming={m.incoming} label={m.contributions?.find(c=>c.kind==='workspace')?.label??`Incoming from ${m.incoming.remote}`} writable={sync} onincorporated={()=>incorporated='pull'}/>{/key}{:else}<p>No incoming contribution is waiting for incorporation.</p>{/if}
 {:else if view==='document'}
  {#if document}<label>Document <select value={document.path} onchange={e=>goto(`?document=${encodeURIComponent(e.currentTarget.value)}`)}>{#each reviewed as d}<option value={d.path}>{d.path.split('/').pop()}</option>{/each}</select></label>{/if}
  <table class="list"><thead><tr><th>Block</th><th>State</th><th>Reason</th></tr></thead><tbody>{#each rows as k}<tr id={`review-${anchorId(k.key)}`}><td><a href={keyUrl(m,k.key)}>{displayNode(m,k.key,document?.path).name}</a></td><td><Badge parts={reviewRowBadge(m,k)}/></td><td>{#each k.acceptance?.causes??[] as c}<a href={`?show=needs-review&block=${encodeURIComponent(k.key)}&cause=${encodeURIComponent(c.identity??[c.kind,c.id??'',c.via??''].join('|'))}`}>{causeLabel(m,c)}</a><br/>{/each}{#each k.incomplete as text}<p>{text}</p>{/each}{#if m.nodes[k.node]?.basis==='unclassified'}<p>Needs classification</p>{/if}{#if m.diagnostics.some(d=>d.code==='loom:missing-proof'&&d.keys.includes(k.key))}<p>Missing proof</p>{/if}<details><summary>Details</summary><p>{k.file} · {m.nodes[k.node]?.basis}</p>{#if k.acceptance}<p>Last accepted by {k.acceptance.author} · {k.acceptance.date}</p>{/if}<p>{reviewFacts(k)}</p><p>Reached by: {m.nodes[k.node]?.reached_by.join(', ')}</p>{#each k.acceptance?.causes??[] as c}{#if c.diff}<DiffView path={c.diff}/>{/if}{/each}</details></td></tr>{:else}<tr><td colspan="3">No blocks in this document.</td></tr>{/each}</tbody></table>
 {:else}<ReviewWorkspace writable={local&&!!m.reviewer?.name}/>{/if}
</div></main>
<style>
 .heading{display:flex;align-items:baseline;justify-content:space-between;gap:20px;padding:0 2px 16px;flex-wrap:wrap}
 .heading h1{font:400 24px/1.2 Georgia,serif;margin:0}
 .heading span{font-size:12px;color:var(--ink-soft)}
 .review-card{border:1px solid var(--rule);border-radius:8px;background:var(--review-paper);min-width:0;overflow:hidden}
 .review-tabs{display:flex;gap:24px;align-items:center;border-bottom:1px solid var(--rule);padding:0 22px;flex-wrap:wrap}
 .review-tabs a{padding:15px 0 12px;text-decoration:none;color:var(--ink-soft);border-bottom:2px solid transparent;white-space:nowrap;font-size:14px}
 .review-tabs a.active{border-color:var(--review-accent);color:var(--review-accent)}
 .reviewer{margin-left:auto;font-size:12px;color:var(--ink-soft);padding:10px 0}
 select{max-width:100%}table{margin:20px;width:calc(100% - 40px)}td{vertical-align:top}details{margin-top:12px}td a{overflow-wrap:anywhere}
 @media(max-width:780px){.review-tabs{gap:18px;padding:0 16px}.reviewer{width:100%;margin:0;padding:0 0 10px}}
</style>
