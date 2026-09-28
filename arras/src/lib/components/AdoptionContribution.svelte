<script lang="ts">
	import { incomingNotice } from '$lib/review/notice.svelte';
	import IncomingMathQueue from '$lib/review/IncomingMathQueue.svelte';
	import type { IncorporationMathReview, IncorporationOutcome, AdoptionReview } from '$lib/manifest/types';
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
	let accepted = $state<string[]>([]);
	let preview = $state<{ token: string; patch: string; paths: string[]; review: IncorporationMathReview } | null>(null);
	const reviewer = $derived(store.manifest?.reviewer?.name ?? '');
	const selected = $derived(contribution.choices?.keys ?? []);
	let active = $state('');
	const items = $derived([...contribution.changes.map(c => ({key:c.key, name:c.name || c.key})), ...(contribution.document_changed ? [{key:'document',name:'Prose & document changes'}] : [])]);
	const activeKey = $derived(items.some(i => i.key === active) ? active : items[0]?.key);
	const activeIndex = $derived(items.findIndex(i => i.key === activeKey));
	const kept = $derived(contribution.choices?.kept ?? []);
	const document = $derived(contribution.choices?.document ?? false);
	const previewIdentity = $derived(JSON.stringify([contribution.copy, contribution.fingerprint, reviewer, [...selected].sort(), document]));
	$effect(() => { void previewIdentity; preview = null; accepted = []; });
	onMount(() => { void can('adopt-decision').then((yes) => writable = yes); });

	async function choose(keys: string[], includeDocument: boolean, keep: string[] = kept) {
		busy = true; error = ''; preview = null;
		const answer = await write('adopt-decision', {copy: contribution.copy, fingerprint: contribution.fingerprint, keys, document: includeDocument, kept: keep.filter(k => !keys.includes(k))});
		if (answer.ok) await store.refresh();
		else error = answer.error?.message ?? 'Could not save selection';
		busy = false;
	}
	async function inspect() {
		busy = true; error = ''; preview = null; accepted = [];
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
		const answer = await write('adopt-finish', {copy: contribution.copy, token: preview.token, review_token: preview.review.token, accept: accepted});
		if (answer.ok) { const outcome=answer.result as unknown as IncorporationOutcome; message=outcome.acceptance_error??`Changes incorporated. ${outcome.accepted?.length??0} ${outcome.accepted?.length===1?"block":"blocks"} accepted; ${outcome.pending?.length??0} remain in Needs review.`; incomingNotice.text=message;onincorporated(contribution.copy); preview=null;await store.refresh(); }
		else error = answer.error?.message ?? 'Could not incorporate the selected changes';
		busy = false;
	}
</script>

<section aria-label={contribution.label}>
	<h2>{contribution.label}</h2>
	<p>Changes will go into <code>{contribution.source}</code> and the node files it uses. You can explicitly accept inspected mathematics when incorporating.</p>
	<p><a href={masterUrl(contribution.copy)}>Open AI draft and its annotations</a></p>
	<p>Choose changes to incorporate now. Unselected proposals remain in the AI draft and will appear again while they differ.</p>
	{#each contribution.issues as issue}<p role="alert">{issue}</p>{/each}
	{#if error}<p role="alert">{error}</p>{/if}
	{#if message}<p role="status">{message} <a href="?show=needs-review">Needs review</a></p>{/if}
	{#if writable && !reviewer}<p>Choose your reviewer name in Settings to select and incorporate changes.</p>{/if}
	{#if !preview}
	{#if writable && reviewer && !contribution.issues.length}
		<button disabled={busy} onclick={() => choose(contribution.changes.map(c => c.key), contribution.document_changed)}>Use all proposed changes</button>
	{/if}
	<div class="workspace">
    <aside aria-label="Proposed changes">{#each items as item}<button class:active={item.key === activeKey} onclick={() => active = item.key}>{item.name}<small>{selected.includes(item.key) || item.key === 'document' && document ? 'Use proposed' : kept.includes(item.key) ? 'Keep current' : 'Not selected'}</small></button>{/each}</aside>
    <div class="inspection"><nav aria-label="Change navigation"><button disabled={activeIndex <= 0} onclick={() => active = items[activeIndex-1].key}>Previous change</button><span>{activeIndex+1} of {items.length}</span><button disabled={activeIndex >= items.length-1} onclick={() => active = items[activeIndex+1].key}>Next change</button></nav>
	{#each contribution.changes.filter(c => c.key === activeKey) as change (change.key)}
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
				<button aria-pressed={kept.includes(change.key)} disabled={busy} onclick={() => choose(selected.filter(k => k !== change.key), document, [...new Set([...kept,change.key])])}>Keep current version</button>
			{/if}
		</section>
	{/each}
	{#if contribution.document_changed && activeKey === 'document'}
		<section class="incoming-change">
			<h3>Prose &amp; document changes</h3><p>Prose, preamble and ordering are incorporated together. This group has no mathematical acceptance action.</p>
			{#if contribution.document_conflict}<p role="alert">Document-level changes conflict. Reconcile them in your editor before including this group.</p>{/if}
			{#if contribution.document_comparison}{@const pair = contribution.document_comparison}<div class="incoming-pair"><div><h4>Current working version</h4>{#if pair.local}<Fragment path={pair.local}/>{:else}<pre>{pair.current}</pre>{/if}</div><div><h4>Proposed version</h4>{#if pair.incoming}<Fragment path={pair.incoming} macroSet={pair.incoming_macros} isolatedMacros/>{:else}<pre>{pair.proposed}</pre>{/if}</div></div>{/if}<details><summary>Source, preamble and ordering changes</summary><pre>{contribution.document_diff}</pre></details>
			{#if writable && reviewer}<label><input type="checkbox" checked={document} disabled={busy || contribution.document_conflict} onchange={(e) => choose(selected, e.currentTarget.checked)}/> Include document-level changes</label>{/if}
		</section>
	{/if}
	</div></div>
	{#if writable && reviewer && !contribution.issues.length}
		<button disabled={busy || (!selected.length && !document)} onclick={inspect}>Preview selected changes</button>
	{/if}
	{/if}
	{#if preview}
		<section class="incoming-change" data-testid="adoption-preview">
			<h3>Review before incorporation</h3><button disabled={busy} onclick={()=>{preview=null;accepted=[];}}>Change selected source</button>
			<p>{selected.length} mathematical block{selected.length === 1 ? "" : "s"}{document ? " and Prose & document changes" : ""} selected. Choose Accept for mathematics you have checked; everything else stays pending.</p>{#key preview.review.token}<IncomingMathQueue review={preview.review} bind:accepted {busy}/>{/key}
            {#if document && contribution.document_comparison}{@const pair = contribution.document_comparison}<h4>Prose &amp; document changes</h4>{#if pair.incoming}<Fragment path={pair.incoming} macroSet={pair.incoming_macros} isolatedMacros/>{:else}<pre>{pair.proposed}</pre>{/if}{/if}
            <details><summary>Exact source patch</summary><pre>{preview.patch || 'No source changes'}</pre></details>
			<button disabled={busy || !preview.patch} onclick={incorporate}>{accepted.length?`Incorporate selected changes & accept ${accepted.length} ${accepted.length===1?"block":"blocks"}`:'Incorporate selected changes'}</button><p>{preview.review.items.length-accepted.length} mathematical blocks remain pending.</p>
		</section>
	{/if}
</section>

<style>
	.workspace{display:grid;grid-template-columns:190px minmax(0,1fr);gap:24px}aside{border-right:1px solid var(--line);padding-right:12px}aside button{display:block;width:100%;text-align:left}aside button.active{background:var(--link-wash)}.inspection{min-width:0}nav{display:flex;align-items:center;justify-content:space-between}@media(max-width:1100px){.workspace{grid-template-columns:1fr}aside{display:flex;flex-wrap:wrap;border-right:0}aside button{width:auto}}
	.incoming-change { border-top: 1px solid var(--line, #aaa); padding: 1rem 0; }
	.incoming-pair { display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr); gap: 1rem; }
	pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 32rem; overflow: auto; }
	small { font-weight: normal; display: block; }
	button { margin: .3rem .5rem .3rem 0; }
	button[aria-pressed='true'] { outline: 2px solid currentColor; }
	[role='alert'] { color: var(--danger, #a22); }
	@media (max-width: 560px) { .incoming-pair { grid-template-columns: 1fr; } }
</style>
