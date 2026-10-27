<script lang="ts">
 // An agent document written from scratch has nothing to compare against, so Incoming offers the one way it is taken in: a new working document started from it, every id it defines made plain.
 import { untrack } from 'svelte';
 import type { StartContribution } from '$lib/manifest/types';
 import { masterUrl } from '$lib/nav';
 import { write } from '$lib/write';
 let { contribution, writable, onstarted }: {contribution: StartContribution; writable: boolean; onstarted: (path: string) => void} = $props();
 // the suggestion is where the field starts; Incoming keys this component by the document, so it is read once
 let to = $state(untrack(() => contribution.to)), busy = $state(false), error = $state('');
 async function start() {
  busy = true; error = '';
  const answer = await write('adopt-start', {copy: contribution.copy, to});
  busy = false;
  if (answer.ok) onstarted((answer.result as unknown as {to: string}).to);
  else error = answer.error?.message ?? 'Could not start the working document';
 }
</script>
<header><h2>{contribution.label}</h2><p class="muted">Written from scratch · no working document started from it</p></header>
<p>It was drafted from none of your documents, so there is nothing to compare it with. <a href={masterUrl(contribution.copy)}>Read it</a>, and start a working document from it when you want to keep it: a new file in your drafting directory, every id it defines made plain. The agent document stays as it is.</p>
{#if writable}
 <form data-testid="start-contribution" onsubmit={(e) => { e.preventDefault(); void start(); }}>
  <label>New working document <input bind:value={to} required /></label>
  <button type="submit" disabled={busy || !to.trim()}>Start a working document from it</button>
 </form>
{:else}
 <p class="muted">This viewer is not served by a publisher that takes writes, so a working document is started from it at the command line.</p>
{/if}
{#if error}<p role="alert">{error}</p>{/if}
<style>
 form{display:flex;flex-wrap:wrap;gap:.6rem;align-items:end;margin:var(--gap-tight) 0}label{display:flex;flex-direction:column;gap:.2rem}input{min-width:18rem;max-width:100%}[role=alert]{color:var(--danger)}
</style>
