<script lang="ts">
 // Review › Needs review: the reviewer's mathematical queue, and each document's blocks with what each needs (`?document=`), which the node page and the diagnostics link into.
 import '$lib/review/review.css';
 import { onMount } from 'svelte';
 import { page } from '$app/state';
 import { goto } from '$app/navigation';
 import { store } from '$lib/manifest/client.svelte';
 import { can } from '$lib/write';
 import { displayNode } from '$lib/nodes/display';
 import { keyUrl, anchorId } from '$lib/nav';
 import { route } from '$lib/paths';
 import { documentKeys } from '$lib/review/documents';
 import { causeLabel } from '$lib/review/evidence';
 import { reviewFacts,reviewRowBadge } from '$lib/badges';
 import NoDrafts from '$lib/components/NoDrafts.svelte';
 import Badge from '$lib/components/Badge.svelte';
 import DiffView from '$lib/components/DiffView.svelte';
 import ReviewHeading from '$lib/review/ReviewHeading.svelte';
 import ReviewWorkspace from '$lib/review/ReviewWorkspace.svelte';
 const m=$derived(store.manifest!);
 const view=$derived(page.url.searchParams.has('document')?'document':'needs-review');
 const reviewed=$derived(m.masters.filter(x=>!x.closed && !x.context_only && x.directory!=='drafting-ai'));
 const document=$derived(reviewed.find(x=>x.path===page.url.searchParams.get('document'))??reviewed.find(x=>x.default)??reviewed[0]);
 const rows=$derived(document?documentKeys(m,document.path):[]);
 let local=$state(false);
 const todo=$derived((m.unresolved??[]).filter(r=>r.status==='needs-review'));
 onMount(()=>{void can('review-decision').then(x=>local=x);});
</script>
<main class="page review-page">
 <ReviewHeading title="Needs review"/>
<div class="review-card"><nav class="review-tabs" aria-label="Needs review views"><a aria-current={view==='needs-review'?'page':undefined} class:active={view==='needs-review'} href={route('/review')}>Queue{todo.length?` (${todo.length})`:''}</a><a aria-current={view==='document'?'page':undefined} class:active={view==='document'} href={document?`?document=${encodeURIComponent(document.path)}`:route('/review')}>Documents</a><span class="reviewer">{m.reviewer?.name?`Reviewing as ${m.reviewer.name}`:'Choose your reviewer name in Settings'}</span></nav>
 {#if !reviewed.length}<NoDrafts what="blocks to review"/>
 {:else if view==='document'}
  {#if document}<label for="review-document">Document</label> <select id="review-document" value={document.path} onchange={e=>goto(`?document=${encodeURIComponent(e.currentTarget.value)}`)}>{#each reviewed as d}<option value={d.path}>{d.path.split('/').pop()}</option>{/each}</select>{/if}
  <table class="list"><thead><tr><th>Block</th><th>State</th><th>Reason</th></tr></thead><tbody>{#each rows as k}<tr id={`review-${anchorId(k.key)}`}><td><a href={keyUrl(m,k.key)}>{displayNode(m,k.key,document?.path).name}</a></td><td><Badge parts={reviewRowBadge(m,k)}/></td><td>{#each k.acceptance?.causes??[] as c}<a href={`?show=needs-review&block=${encodeURIComponent(k.key)}&cause=${encodeURIComponent(c.identity??[c.kind,c.id??'',c.via??''].join('|'))}`}>{causeLabel(m,c)}</a><br/>{/each}{#each k.incomplete as text}<p>{text}</p>{/each}{#if m.nodes[k.node]?.basis==='unclassified'}<p>Needs classification</p>{/if}{#if m.diagnostics.some(d=>d.code==='loom:missing-proof'&&d.keys.includes(k.key))}<p>Missing proof</p>{/if}<details><summary>Details</summary><p>{k.file} · {m.nodes[k.node]?.basis}</p>{#if k.acceptance}<p>Last accepted by {k.acceptance.author} · {k.acceptance.date}</p>{/if}<p>{reviewFacts(k)}</p><p>Reached by: {m.nodes[k.node]?.reached_by.join(', ')}</p>{#each k.acceptance?.causes??[] as c}{#if c.diff}<DiffView path={c.diff}/>{/if}{/each}</details></td></tr>{:else}<tr><td colspan="3">No blocks in this document.</td></tr>{/each}</tbody></table>
 {:else}<ReviewWorkspace writable={local&&!!m.reviewer?.name}/>{/if}
</div></main>
<style>
 .review-card{border:1px solid var(--rule);border-radius:8px;background:var(--review-paper);min-width:0;overflow:hidden}
 .review-tabs{display:flex;gap:24px;align-items:center;border-bottom:1px solid var(--rule);padding:0 22px;flex-wrap:wrap}
 .review-tabs a{padding:15px 0 12px;text-decoration:none;color:var(--ink-soft);border-bottom:2px solid transparent;white-space:nowrap;font-size:14px}
 .review-tabs a.active{border-color:var(--review-accent);color:var(--review-accent)}
 .reviewer{margin-left:auto;font-size:12px;color:var(--ink-soft);padding:10px 0}
 select{max-width:100%}table{margin:20px;width:calc(100% - 40px)}td{vertical-align:top}details{margin-top:12px}td a{overflow-wrap:anywhere}
 @media(max-width:780px){.review-tabs{gap:18px;padding:0 16px}.reviewer{width:100%;margin:0;padding:0 0 10px}}
</style>
