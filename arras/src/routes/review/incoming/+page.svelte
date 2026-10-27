<script lang="ts">
 // Review › Incoming: what waits to be taken in — a collaborator's fetched pull, an agent document's changes to the document it was drafted from, and an agent document written from scratch, which starts a working document — one at a time, chosen from one list.
 import { incomingNotice } from '$lib/review/notice.svelte';
 import '$lib/review/review.css';
 import { onMount } from 'svelte';
 import { store } from '$lib/manifest/client.svelte';
 import { can } from '$lib/write';
 import { masterUrl } from '$lib/nav';
 import { route } from '$lib/paths';
 import AdoptionContribution from '$lib/components/AdoptionContribution.svelte';
 import IncomingPull from '$lib/review/IncomingPull.svelte';
 import ReviewHeading from '$lib/review/ReviewHeading.svelte';
 import StartContribution from '$lib/review/StartContribution.svelte';
 import type { AdoptionReview, StartContribution as Start } from '$lib/manifest/types';
 const m=$derived(store.manifest!);
 const adoptions=$derived((m.contributions??[]).filter((x):x is AdoptionReview=>x.kind==='adopt'));
 const starts=$derived((m.contributions??[]).filter((x):x is Start=>x.kind==='start'));
 const offered=$derived([...adoptions,...starts]);
 let source=$state(''),sync=$state(false),incorporated=$state(''),started=$state(''),startable=$state(false);
 const selectedSource=$derived(offered.some(x=>x.copy===source)?source:m.incoming?'':offered[0]?.copy??'');
 const adoption=$derived(adoptions.find(x=>x.copy===selectedSource));
 const starting=$derived(starts.find(x=>x.copy===selectedSource));
 onMount(()=>{void can('sync-incorporate').then(x=>sync=x);void can('adopt-start').then(x=>startable=x);});
</script>
<main class="page review-page">
 <ReviewHeading title="Incoming"/>
 {#if incomingNotice.text}<p role="status">{incomingNotice.text}</p>{/if}
<div class="review-card"><div class="incoming">
  {#if started}<p role="status">Started <a href={masterUrl(started)}>{started.split('/').pop()}</a> from the agent document.</p>{/if}
  {#if incorporated}<p role="status">{#if !incomingNotice.text}Changes incorporated. {/if}<a href={route('/review')}>Review affected mathematics</a>{#if incorporated!=='pull'} · <a href={masterUrl(incorporated)}>The agent document and its annotations</a>{/if}</p>{/if}
  {#if offered.length+(m.incoming?1:0)>1}<label>Contribution <select value={selectedSource} onchange={e=>source=e.currentTarget.value}>{#if m.incoming}<option value="">Fetched pull</option>{/if}{#each offered as a}<option value={a.copy}>{a.label}</option>{/each}</select></label>{/if}
  {#if starting}{#key starting.copy}<StartContribution contribution={starting} writable={startable&&!!m.reviewer?.name} onstarted={path=>started=path}/>{/key}{:else if adoption}{#key adoption.copy}<AdoptionContribution contribution={adoption} onincorporated={copy=>incorporated=copy}/>{/key}{:else if m.incoming}{#key m.incoming.commit}<IncomingPull incoming={m.incoming} label={m.contributions?.find(c=>c.kind==='workspace')?.label??`Incoming from ${m.incoming.workspace}`} writable={sync} onincorporated={()=>incorporated='pull'}/>{/key}{:else}<p>No incoming contribution is waiting for incorporation.</p>{/if}
</div></div></main>
<style>
 .review-card{border:1px solid var(--rule);border-radius:8px;background:var(--review-paper);min-width:0;overflow:hidden}
 select{max-width:100%}
</style>
