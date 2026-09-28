<script lang="ts">
 import type { IncorporationMathReview } from '$lib/manifest/types';
 import IncomingMath from './IncomingMath.svelte';
 let {review, accepted=$bindable<string[]>([]), busy=false}: {review:IncorporationMathReview;accepted?:string[];busy?:boolean}=$props();
 let index=$state(0),kept=$state<string[]>([]);
 const item=$derived(review.items[Math.min(index,review.items.length-1)]);
</script>
{#if item}<div class="queue"><aside aria-label="Mathematical items">{#each review.items as row,i}<button class:active={row.key===item.key} onclick={()=>index=i}>{row.name}<small>{accepted.includes(row.key)?'Accept on incorporation':kept.includes(row.key)?'Keep for review':'Pending'}</small></button>{/each}</aside><section>{#key item.key}<IncomingMath {item} bind:accepted bind:kept {busy}/>{/key}<nav aria-label="Mathematical navigation"><button disabled={index===0} onclick={()=>index--}>Previous block</button><span>{index+1} of {review.items.length}</span><button disabled={index>=review.items.length-1} onclick={()=>index++}>Next block</button></nav></section></div>{:else}<p>No mathematical blocks need a decision for this revision.</p>{/if}
<style>.queue{display:grid;grid-template-columns:190px minmax(0,1fr);gap:24px}.queue>section{min-width:0}aside{border-right:1px solid var(--rule);padding-right:12px}aside button{display:block;width:100%;text-align:left}aside button.active{background:var(--review-wash)}small{display:block;color:var(--ink-soft)}nav{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:20px}@media(max-width:1100px){.queue{grid-template-columns:1fr}aside{display:flex;flex-wrap:wrap;border:0}aside button{width:auto}}</style>
