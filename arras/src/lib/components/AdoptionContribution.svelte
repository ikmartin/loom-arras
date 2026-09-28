<script lang="ts">
	import type { AdoptionReview } from '$lib/manifest/types';
	import { store } from '$lib/manifest/client.svelte';
	import { can, write } from '$lib/write';
	import { onMount } from 'svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { keyUrl, masterUrl } from '$lib/nav';

	let { contribution, onincorporated }: { contribution: AdoptionReview; onincorporated: (copy: string) => void } = $props();
	let writable = $state(false);
	let busy = $state(false);
	let error = $state('');
	let message = $state('');
	let preview = $state<{ token: string; patch: string; paths: string[] } | null>(null);
	const reviewer = $derived(store.manifest?.reviewer?.name ?? '');
	const selected = $derived(contribution.choices?.keys ?? []);
	const document = $derived(contribution.choices?.document ?? false);
	const previewIdentity = $derived(JSON.stringify([contribution.copy, contribution.fingerprint, reviewer, [...selected].sort(), document]));
	$effect(() => { void previewIdentity; preview = null; });
	onMount(() => { void can('adopt-decision').then((yes) => writable = yes); });

	async function choose(keys: string[], includeDocument: boolean) {
		busy = true; error = ''; preview = null;
		const answer = await write('adopt-decision', {copy: contribution.copy, fingerprint: contribution.fingerprint, keys, document: includeDocument});
		if (answer.ok) await store.refresh();
		else error = answer.error?.message ?? 'Could not save selection';
		busy = false;
	}
	async function inspect() {
		busy = true; error = ''; preview = null;
		const inspected = previewIdentity;
		const answer = await write('adopt-preview', {copy: contribution.copy, fingerprint: contribution.fingerprint});
		if (answer.ok && inspected === previewIdentity) preview = answer.result as unknown as typeof preview;
		else if (answer.ok) error = 'The contribution changed. Preview the selected changes again.';
		else error = answer.error?.message ?? 'Could not prepare the selected changes';
		busy = false;
	}
	async function incorporate() {
		if (!preview) return;
		busy = true; error = '';
		const answer = await write('adopt-finish', {copy: contribution.copy, token: preview.token});
		if (answer.ok) { message = 'Changes incorporated. Continue in Needs review to check the mathematics.'; onincorporated(contribution.copy); preview = null; await store.refresh(); }
		else error = answer.error?.message ?? 'Could not incorporate the selected changes';
		busy = false;
	}
</script>

<section aria-label={contribution.label}>
	<h2>{contribution.label}</h2>
	<p>Changes will go into <code>{contribution.source}</code> and the node files it uses. Incorporation does not accept mathematics.</p>
	<p><a href={masterUrl(contribution.copy)}>Open AI draft and its annotations</a></p>
	<p>Choose changes to incorporate now. Unselected proposals remain in the AI draft and will appear again while they differ.</p>
	{#each contribution.issues as issue}<p role="alert">{issue}</p>{/each}
	{#if error}<p role="alert">{error}</p>{/if}
	{#if message}<p role="status">{message} <a href="?show=needs-review">Needs review</a></p>{/if}
	{#if writable && !reviewer}<p>Choose your reviewer name in Settings to select and incorporate changes.</p>{/if}
	{#if writable && reviewer && !contribution.issues.length}
		<button disabled={busy} onclick={() => choose(contribution.changes.map(c => c.key), contribution.document_changed)}>Use all proposed changes</button>
	{/if}
	{#each contribution.changes as change (change.key)}
		<section class="incoming-change" data-testid={`adoption-${change.key}`}>
			<h3>{change.name || change.key} <small>{change.class === 'new' ? 'New result' : change.class === 'separate-result' ? 'Separate result from' : 'Proposed revision of'} {change.key}</small></h3>
			{#if change.class === 'conflict'}<p role="alert">Both versions changed. Reconcile the text in your editor, then refresh Incoming.</p>{/if}
			{#if change.class === 'removed'}<p>Remove from this document. Reusable node files remain available.</p>{/if}
			{#if change.class === 'separate-result'}<p>This result belongs to another document. Incorporate it as a separate result.</p>{/if}
			{#if !change.math_changed}<p>This changes source details, without changing the mathematical text.</p>{/if}
			<div class="incoming-pair">
				<div><h4>Current working version</h4>{#if change.local}<Fragment path={change.local}/>{:else}<pre>{change.current || 'No current definition'}</pre>{/if}</div>
				<div><h4>Proposed version</h4>{#if change.incoming}<Fragment path={change.incoming} macroSet={change.incoming_macros} isolatedMacros/>{:else}<pre>{change.proposed || 'Removed from document'}</pre>{/if}</div>
			</div>
			{#if change.documents.length > 1}<p>Used in: {change.documents.join(', ')}</p>{/if}
			{#if change.affected.length}<p>Potentially affected: {#each change.affected as affected}<a href={keyUrl(store.manifest!, affected.key)}>{affected.key}</a>{' '}{/each}</p>{/if}
			{#if writable && reviewer}
				<button aria-pressed={selected.includes(change.key)} disabled={busy} onclick={() => choose([...new Set([...selected, change.key])], document)}>Use proposed version</button>
				<button aria-pressed={!selected.includes(change.key)} disabled={busy} onclick={() => choose(selected.filter(k => k !== change.key), document)}>Keep current version</button>
			{/if}
		</section>
	{/each}
	{#if contribution.document_changed}
		<section class="incoming-change">
			<h3>Prose, preamble and ordering</h3>
			{#if contribution.document_conflict}<p role="alert">Document-level changes conflict. Reconcile them in your editor before including this group.</p>{/if}
			<pre>{contribution.document_diff}</pre>
			{#if writable && reviewer}<label><input type="checkbox" checked={document} disabled={busy} onchange={(e) => choose(selected, e.currentTarget.checked)}/> Include document-level changes</label>{/if}
		</section>
	{/if}
	{#if writable && reviewer && !contribution.issues.length}
		<button disabled={busy || (!selected.length && !document)} onclick={inspect}>Preview selected changes</button>
	{/if}
	{#if preview}
		<section class="incoming-change" data-testid="adoption-preview">
			<h3>Exact changes to incorporate</h3>
			<pre>{preview.patch || 'No source changes'}</pre>
			<button disabled={busy || !preview.patch} onclick={incorporate}>Incorporate selected changes</button>
		</section>
	{/if}
</section>

<style>
	.incoming-change { border-top: 1px solid var(--line, #aaa); padding: 1rem 0; }
	.incoming-pair { display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr); gap: 1rem; }
	pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 32rem; overflow: auto; }
	small { font-weight: normal; display: block; }
	button { margin: .3rem .5rem .3rem 0; }
	button[aria-pressed='true'] { outline: 2px solid currentColor; }
	[role='alert'] { color: var(--danger, #a22); }
	@media (max-width: 700px) { .incoming-pair { grid-template-columns: 1fr; } }
</style>
