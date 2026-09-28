<script lang="ts">
 import Fragment from '$lib/fragments/Fragment.svelte';
 import type { IncorporationMathItem } from '$lib/manifest/types';
 let {item, accepted=$bindable<string[]>([]), busy=false, kept=$bindable<string[]>([])}: {item:IncorporationMathItem;accepted?:string[];busy?:boolean;kept?:string[]}=$props();
 let loaded=$state('');
 const held=$derived(kept.includes(item.key));
 const chosen=$derived(accepted.includes(item.key));
 function choose(accept:boolean){accepted=[...accepted.filter(k=>k!==item.key),...(accept?[item.key]:[])];kept=[...kept.filter(k=>k!==item.key),...(!accept?[item.key]:[])];}
</script>
<h2>{item.name}</h2><p class="reason">{item.reason}</p>
<div class="math-pair"><section><h3>Current working version</h3>{#if item.local}<Fragment path={item.local.path} previewMacros={item.local.macros} isolatedMacros/>{:else}<p>New mathematical block</p>{/if}</section><section><h3>After incorporation</h3><Fragment path={item.proposed.path} previewMacros={item.proposed.macros} isolatedMacros onmounted={()=>loaded=item.key}/></section></div>
<div class="decisions" aria-label={`Mathematical decision for ${item.name}`}><strong>{chosen?'Accept on incorporation':held?'Keep for review':'Pending'}</strong><button class:primary={chosen} aria-pressed={chosen} disabled={busy||loaded!==item.key||!!item.unavailable} onclick={()=>choose(true)}>Accept</button><button class:primary={held} aria-pressed={held} disabled={busy} onclick={()=>choose(false)}>Keep for review</button></div>
{#if item.unavailable}<p>{item.unavailable} This block will stay in mathematical review.</p>{/if}
<p class="hint">Acceptance is recorded only when you incorporate. Leaving this item pending keeps it in Needs review.</p>
<style>
 h2{font:400 23px/1.3 Georgia,serif;margin:0 0 10px}h3,.reason,.hint{font-size:12px;color:var(--ink-soft)}.math-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.math-pair>section{min-width:0}.math-pair>section+section{border-left:1px solid var(--rule);padding-left:24px}.decisions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:24px}.decisions strong{font-size:12px;font-weight:400;margin-right:auto}.math-pair :global(.review-changed){color:inherit;background:var(--review-add)}.math-pair :global(.fragment p){text-align:left}.math-pair :global(.fragment){font:16px/1.75 Georgia,serif} @media(max-width:560px){.math-pair{grid-template-columns:1fr}.math-pair>section+section{border-left:0;border-top:1px solid var(--rule);padding:18px 0}}
</style>
