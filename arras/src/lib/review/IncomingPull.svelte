<script lang="ts">
 import { incomingNotice } from './notice.svelte';
 import { untrack } from 'svelte';
 import IncomingMath from './IncomingMath.svelte';
 import type { IncorporationMathReview, IncorporationOutcome, IncomingReview } from '$lib/manifest/types';
 import Fragment from '$lib/fragments/Fragment.svelte';
 import { store } from '$lib/manifest/client.svelte';
 import { displayNode } from '$lib/nodes/display';
 import { write } from '$lib/write';
 let { incoming, label, writable, onincorporated }: {incoming:IncomingReview;label:string;writable:boolean;onincorporated:()=>void}=$props();
 let index=$state(0),busy=$state(false),error=$state('');
 let review=$state<IncorporationMathReview|null>(null), accepted=$state<string[]>([]),kept=$state<string[]>([]), preparing=$state(false);
 const identity=$derived(JSON.stringify([incoming.commit,incoming.base,store.manifest?.reviewer?.name]));
 const passages=$derived([...incoming.changes, ...(review?.items.filter(r=>!incoming.changes.some(c=>c.key===r.key)).map(r=>({key:r.key,name:r.name,kind:'edited' as const,category:undefined,conflict:false,local:null,incoming:null,current:'',proposed:'',incoming_macros:'',affected:[],local_changed:false,already_local:false}))??[])]);
 const math=$derived(review?.items.find(r=>r.key===change?.key));
 $effect(()=>{void identity;if(writable)untrack(()=>{void prepare();});});
 async function prepare(){const started=identity;preparing=true;review=null;accepted=[];kept=[];error='';const r=await write('sync-preview',{incoming:incoming.commit,base:incoming.base});if(started!==identity)return;if(r.ok)review=r.result as unknown as IncorporationMathReview;else error=r.error?.message??'Could not prepare mathematical review';preparing=false;}

 const change=$derived(passages[Math.min(index,passages.length-1)]);
 const title=(key:string,name?:string)=>name??displayNode(store.manifest!,key).name;
 async function incorporate(){busy=true;error='';const r=await write('sync-incorporate',{incoming:incoming.commit,base:incoming.base,...(review?{review_token:review.token,accept:accepted}:{})});if(r.ok){const outcome=r.result as unknown as IncorporationOutcome;incomingNotice.text=outcome.acceptance_error??`Pull incorporated. ${outcome.accepted?.length??0} ${outcome.accepted?.length===1?"block":"blocks"} accepted; ${outcome.pending?.length??0} remain in Needs review.`;await store.refresh();onincorporated();}else error=r.error?.message??'Could not incorporate the pull';busy=false;}
</script>
<header><h2>{label}</h2><p class="muted">Fetched revision · not incorporated</p><details><summary>Contribution details</summary><p>{incoming.remote}/{incoming.branch} · {incoming.commit.slice(0,12)} · base {incoming.base.slice(0,12)}</p></details></header>
{#each incoming.issues??[] as issue}<p role="alert">{issue}</p>{/each}
{#if error}<p role="alert">{error}</p>{#if writable}<button disabled={busy||preparing} onclick={prepare}>Refresh mathematical preview</button>{/if}{/if}
<div class="layout"><aside aria-label="Incoming changes">{#each passages as c,i}<button class:active={change?.key===c.key} onclick={()=>index=i}>{title(c.key,c.name)}<small>{c.category==='prose'?'Prose':accepted.includes(c.key)?'Accept on incorporation':kept.includes(c.key)?'Keep for review':review&&!review.items.some(r=>r.key===c.key)?'Source change':'Pending'}</small></button>{/each}</aside><section class="content">
{#if change}<label class="compact">Changed passage <select value={index} onchange={e=>index=Number(e.currentTarget.value)}>{#each passages as c,i}<option value={i}>{title(c.key,c.name)}</option>{/each}</select></label>{#if math}{#key math.key}<IncomingMath item={math} bind:accepted bind:kept {busy}/>{/key}{:else}<h2>{title(change.key,change.name)}</h2>{#if change.conflict}<p role="alert">Both versions changed. Reconcile the source before incorporation.</p>{/if}<div class="pair"><section><h3>Current working document</h3>{#if change.local}<Fragment path={change.local}/>{:else}<pre>{change.current??'No current passage'}</pre>{/if}</section><section><h3>Fetched version</h3>{#if change.incoming}<Fragment path={change.incoming} macroSet={change.incoming_macros} isolatedMacros/>{:else}<pre>{change.proposed??'No incoming passage'}</pre>{/if}</section></div>{#if change.category==='prose'}<p class="muted">Prose outside mathematical blocks has no acceptance task. Formula and document-context changes retain their dependency checks.</p>{/if}{/if}<nav aria-label="Change navigation"><span>{index+1} of {passages.length}</span><button disabled={index===0} onclick={()=>index--}>Previous change</button><button disabled={index>=passages.length-1} onclick={()=>index++}>Next change</button></nav>{:else}<p>Inspect the changed source files below.</p>{/if}
</section></div>
<details><summary>Changed source files and diffs ({incoming.files.length})</summary>{#each incoming.files as file}<details><summary>{file.path} · {file.status}</summary>{#if file.diff}<pre>{file.diff}</pre>{:else}<p>No text diff is available for this file. Inspect the fetched file before incorporating this pull.</p>{/if}</details>{/each}</details>
<footer data-testid="incoming-incorporation"><p>Applies the whole pull. {#if review}{review.items.length-accepted.length} mathematical blocks remain pending.{:else}Mathematics remains pending unless explicitly accepted.{/if} Unvisited items are not accepted.</p>{#if preparing}<p>Preparing mathematical preview…</p>{/if}{#if writable}<button disabled={busy||preparing||!!incoming.issues?.length||incoming.changes.some(c=>c.conflict)} onclick={incorporate}>{busy?'Incorporating…':accepted.length?`Incorporate pull & accept ${accepted.length} ${accepted.length===1?"block":"blocks"}`:'Incorporate pull'}</button>{/if}</footer>
<style>
 .layout{display:grid;grid-template-columns:190px minmax(0,1fr)}aside{border-right:1px solid var(--rule);padding:15px}aside button{display:block;width:100%;text-align:left;border:0;padding:10px;background:none}aside button.active{background:var(--link-wash)}small{display:block;color:var(--ink-soft)}.content{padding:20px;min-width:0}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.pair>section{min-width:0}.pair>section+section{border-left:1px solid var(--rule);padding-left:24px}h3,.muted,summary{font-size:12px;color:var(--ink-soft)}pre{white-space:pre-wrap;overflow-wrap:anywhere}.compact{display:none}nav,footer{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:24px;padding-top:16px;border-top:1px solid var(--rule)}nav span,footer p{flex:1}details{margin:12px 0}.pair :global(.review-changed){background:var(--state-stale-wash)}
 @media(max-width:1100px){.layout{grid-template-columns:1fr}aside{display:none}.compact{display:block}.content{padding:18px 0}}
 @media(max-width:560px){.pair{grid-template-columns:1fr}.pair>section+section{border-left:0;border-top:1px solid var(--rule);padding:18px 0}select{max-width:100%}}
</style>
