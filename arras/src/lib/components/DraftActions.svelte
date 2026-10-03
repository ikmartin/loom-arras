<script lang="ts">
 import type { Master } from '$lib/manifest/types';
 import { store } from '$lib/manifest/client.svelte';
 import { can, write } from '$lib/write';
 import { dataUrl } from '$lib/paths';
 import { masterUrl } from '$lib/nav';
 import { onMount } from 'svelte';
 let {master}: {master: Master} = $props();
 let writable = $state(false);
 let busy = $state(false);
 let error = $state('');
 let message = $state('');
 let confirmation = $state('');
 let pdf = $state('');
 onMount(() => { void can('adopt-close').then(ok => writable = ok); });
 async function action(endpoint: string, confirmed = false) {
  busy = true; error = ''; message = '';
  const answer = await write(endpoint, {copy: master.path, confirmed});
  if (answer.ok) {
   const result = answer.result as unknown as {confirmation_required?: boolean; message?: string; pdf?: string; conflicts?: string[]};
   if (result.confirmation_required) confirmation = result.message ?? 'Close with unapplied changes?';
   else { confirmation = ''; message = result.message ?? (result.conflicts?.length ? 'Some edits conflict. Resolve them in your editor before incorporating.' : 'Draft updated.'); pdf = result.pdf ?? ''; await store.refresh(); }
  } else error = answer.error?.message ?? 'Could not update the draft';
  busy = false;
 }
</script>
<div class="draft-actions">
 {#if master.scope?.kind === 'section'}
  <p>AI draft of <strong>{master.scope.title}</strong> in <a href={masterUrl(master.copy_of!)}>{master.copy_of}</a>. References outside this section use context saved {master.context_when?.slice(0,10)}.{#if master.context_document} <a href={masterUrl(master.context_document)}>Read saved paper context</a>.{/if}</p>
  {#if master.context_changed && !master.closed}<p role="status">The paper context has changed. Refresh to bring in current context while keeping the draft’s edits.</p>{/if}
 {/if}
 {#if writable && store.manifest?.reviewer?.name}
  {#if master.closed}<button disabled={busy} onclick={() => action('adopt-reopen')}>Reopen draft</button>
  {:else}
   <button disabled={busy} onclick={() => action('adopt-refresh')}>Update draft from paper</button>
   {#if master.scope?.kind === 'section'}<button disabled={busy} onclick={() => action('adopt-paper')}>Preview in paper</button>{/if}
   <button disabled={busy} onclick={() => action('adopt-close')}>Close draft</button>
  {/if}
 {/if}
 {#if confirmation}<div role="alert"><p>{confirmation}</p><button disabled={busy} onclick={() => action('adopt-close', true)}>Close and keep saved copy</button><button disabled={busy} onclick={() => confirmation = ''}>Cancel</button></div>{/if}
 {#if error}<p role="alert">{error}</p>{/if}
 {#if message}<p role="status">{message}</p>{/if}
 {#if pdf}<p><a href={dataUrl(pdf)} target="_blank" rel="noreferrer">Open preview PDF</a> · saved paper context with this draft substituted</p>{/if}
</div>
<style>.draft-actions{padding:var(--gap-tight) var(--gap-wide);border-bottom:1px solid var(--line)}button{margin:0 .6rem .4rem 0}[role=alert]{color:var(--danger)}</style>
