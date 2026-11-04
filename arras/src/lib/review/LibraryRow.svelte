<script lang="ts" module>
	/** What the publisher serves, so a line is offered only where it can act. */
	export interface Caps {
		runs: boolean;
		upload: boolean;
		ask: boolean;
		ignore: boolean;
		remove: boolean;
	}
	/** An act on one work. */
	export type RowAct = 'run' | 'redo' | 'upload' | 'ask' | 'ignore' | 'unignore' | 'remove';
	/** What an act answered: whether it was done, and what to say in the row. */
	export interface Done {
		ok: boolean;
		said: string;
	}
</script>

<script lang="ts">
	// One work on the library's page (plan 0.24.4): what it is and who wrote it, whether its paper is filed, how much has been read off it and from where, how much the person verified and what waits for them, its overview, where they cite it, and its problems, each with what fixes it. Its ⋯ menu holds what can be done to it, each line only where the publisher serves it and where it applies; the acts themselves are the page's (`onact`), which follows a run and asks for the network once for every row. Stopping asking for a work's paper asks why, and removing a work asks first, in the row.
	import { goto } from '$app/navigation';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import ToolbarMenu from '$lib/workspace/ToolbarMenu.svelte';
	import ToolbarItem from '$lib/workspace/ToolbarItem.svelte';
	import type { FixAct, LedgerRow, Problem } from '$lib/library';
	import type { Reference } from '$lib/manifest/types';
	import { workUrl } from '$lib/nav';
	import { route } from '$lib/paths';

	let {
		row,
		ref,
		problems,
		caps,
		select = false,
		checked = false,
		ontoggle,
		onact
	}: {
		row: LedgerRow;
		ref: Reference;
		problems: Problem[];
		caps: Caps;
		/** Rows can be selected, for the acts on several at once. */
		select?: boolean;
		checked?: boolean;
		ontoggle?: () => void;
		/** Do `act` to this work, with `why` for a claim about it. */
		onact: (act: RowAct, why?: string) => Promise<Done>;
	} = $props();

	const ck = $derived(row.citekey);
	let prompt = $state<'ignore' | 'unignore' | 'remove' | null>(null);
	let why = $state('');
	let said = $state('');
	let busy = $state(false);

	// what can be done to it now: a run while something is missing, again from scratch once it is digested; asking for its paper only while it has none
	const missing = $derived(!row.filed || !ref.artifacts?.source || !row.digest);
	const removable = $derived(row.added && row.cited === 0);
	const FIX: Record<FixAct, string> = { run: 'Fetch and digest it', redo: 'Digest it again', upload: 'Upload a PDF', ignore: 'Stop asking for its paper…' };
	const fixLabel = (p: Problem, f: FixAct) => (p.code === 'lookup-failed' && f === 'run' ? 'Try again' : FIX[f]);
	const offered = (f: FixAct) => (f === 'run' || f === 'redo' ? caps.runs : f === 'upload' ? caps.upload : caps.ignore && !row.unreadable && !row.filed);

	async function act(a: RowAct, reason?: string): Promise<void> {
		if (a === 'ignore' || a === 'unignore' || a === 'remove') {
			if (prompt !== a) {
				prompt = a;
				why = '';
				said = '';
				return;
			}
		}
		busy = true;
		const done = await onact(a, reason);
		busy = false;
		said = done.said;
		// a refusal leaves the question standing, so the reason can be changed and sent again
		if (done.ok) prompt = null;
	}

	async function copy(): Promise<void> {
		try {
			await navigator.clipboard.writeText(ref.bibtex ?? '');
			said = 'BibTeX copied';
		} catch {
			said = 'Could not copy: open its Info and select the entry';
		}
	}
</script>

<tr data-testid="ledger-{ck}" class:picked={checked}>
	{#if select}
		<td class="pick"><input type="checkbox" {checked} onchange={() => ontoggle?.()} aria-label="Select {ck}" data-testid="select-{ck}" /></td>
	{/if}
	<td class="work">
		<a class="title" href={workUrl(ck)}><Tex text={row.title} /></a>
		<span class="byline">
			<code>{ck}</code>{#if row.authors}{' · '}<Tex text={row.authors} />{/if}
			{#if row.added}<span class="held" data-testid="added-{ck}">· added by hand</span>{/if}
			{#if row.versions.length}<span class="versions" data-testid="versions-{ck}">· also {#each row.versions as v, i (v)}{i ? ', ' : ''}<a href={workUrl(v)}><code>{v}</code></a>{/each}</span>{/if}
			{#if row.unreadable}<span class="held" data-testid="unreadable-{ck}">· declared unreadable</span>{/if}
			{#if row.open}<a class="held open" href={workUrl(ck)} data-testid="open-{ck}">· {row.open} open</a>{/if}
			<WorkLinks {ref} />
		</span>
		{#each problems as p (p.code)}
			<span class="problem" data-testid="problem-{ck}" data-code={p.code}>
				<span class="said">{p.text}</span>
				{#each p.fixes.filter(offered) as f (f)}<button type="button" class="fix" disabled={busy} onclick={() => void act(f === 'ignore' ? 'ignore' : f)} data-testid="fix-{f}">{fixLabel(p, f)}</button>{/each}
			</span>
		{/each}
		{#if prompt === 'ignore' || prompt === 'unignore'}
			<form
				class="prompt"
				onsubmit={(e) => {
					e.preventDefault();
					if (why.trim()) void act(prompt!, why.trim());
				}}
			>
				<label>
					{prompt === 'ignore' ? 'Why stop asking for its paper?' : 'Why ask for its paper again?'}
					<input bind:value={why} placeholder={prompt === 'ignore' ? 'a living document with no fixed version' : 'a version can be had after all'} data-testid="ignore-why" />
				</label>
				<button type="submit" class="fix" disabled={busy || !why.trim()} data-testid="ignore-go">{prompt === 'ignore' ? 'Stop asking' : 'Ask again'}</button>
				<button type="button" class="fix" onclick={() => (prompt = null)}>Cancel</button>
			</form>
		{:else if prompt === 'remove'}
			<span class="prompt">
				Remove {ck} from the library? A paper stored for it is set aside, not deleted.
				<button type="button" class="fix danger" disabled={busy} onclick={() => void act('remove')} data-testid="remove-go">Remove</button>
				<button type="button" class="fix" onclick={() => (prompt = null)}>Cancel</button>
			</span>
		{/if}
		{#if said}<span class="row-said" role="status" data-testid="row-said-{ck}">{said}</span>{/if}
	</td>
	<td data-testid="paper-{ck}">{#if row.filed}filed{:else}<span class="nope">—</span>{/if}</td>
	<td class="num">
		<span data-testid="digest-{ck}">{row.digest || '—'}</span>{#if row.digest && row.from}<span class="from">({row.from === 'both' ? 'source and pages' : row.from})</span>{/if}
	</td>
	<td class="num">
		<span data-testid="verified-{ck}">{row.verified || '—'}</span>
		{#if row.proposed}<a class="pending" href={route('/review/proposed') + '?work=' + encodeURIComponent(ck) + '#queue'} data-testid="pending-{ck}">{row.proposed} to verify</a>{/if}
	</td>
	<td data-testid="overview-{ck}">{#if row.overview}✓{:else}<span class="nope">—</span>{/if}</td>
	<td class="num" data-testid="cited-{ck}">{#if row.cited}{row.cited}{:else}<span class="nope">not cited</span>{/if}</td>
	<td class="acts">
		<ToolbarMenu label="⋯" caret={false} name="What to do with {ck}" menuName="Acts on {ck}" testid="menu-{ck}" menuTestid="menu-items-{ck}" width={250}>
			<ToolbarItem label="Open its info" name="Open the Info of {ck}" testid="act-info" onclick={() => void goto(workUrl(ck) + '?view=info')} />
			{#if caps.runs}
				{#if missing}
					<ToolbarItem label="Fetch and digest it" name="Fetch and digest {ck}" testid="act-run" onclick={() => void act('run')} />
				{/if}
				{#if row.digest}
					<ToolbarItem label="Digest it again" name="Digest {ck} again from scratch" testid="act-redo" onclick={() => void act('redo')} />
				{/if}
			{/if}
			{#if caps.upload && !row.filed}<ToolbarItem label="Upload a PDF…" name="Upload a PDF of {ck}" testid="act-upload" onclick={() => void act('upload')} />{/if}
			{#if caps.ask && !row.overview}<ToolbarItem label="Ask an agent for an overview" name="Ask an agent for the overview of {ck}" testid="act-ask" onclick={() => void act('ask')} />{/if}
			{#if ref.bibtex}<ToolbarItem label="Copy BibTeX" name="Copy the BibTeX entry of {ck}" testid="act-copy" onclick={() => void copy()} />{/if}
			{#if caps.ignore && !row.filed && !ref.artifacts?.source}
				<hr />
				{#if row.unreadable}
					<ToolbarItem label="Ask for its paper again…" name="Ask for the paper of {ck} again" testid="act-unignore" onclick={() => void act('unignore')} />
				{:else}
					<ToolbarItem label="Stop asking for its paper…" name="Stop asking for the paper of {ck}" testid="act-ignore" onclick={() => void act('ignore')} />
				{/if}
			{/if}
			{#if caps.remove && removable}
				<hr />
				<ToolbarItem label="Remove from the library…" name="Remove {ck} from the library" testid="act-remove" onclick={() => void act('remove')} />
			{/if}
		</ToolbarMenu>
	</td>
</tr>

<style>
	.picked {
		background: var(--link-wash);
	}
	.pick {
		width: 1.5em;
	}
	.work {
		max-width: 28rem;
	}
	a.title {
		display: block;
		font-family: var(--body-face);
		font-size: 13px;
		line-height: 1.4;
		font-weight: 500;
	}
	.byline {
		display: block;
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		line-height: 1.5;
	}
	.byline code {
		font-size: 9px;
		background: none;
		padding: 0;
	}
	.held,
	.versions {
		margin-left: 0.2em;
	}
	.versions a,
	a.open {
		color: inherit;
	}
	.problem,
	.prompt,
	.row-said {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 8px;
		margin-top: 4px;
		font-family: var(--sans);
		font-size: 11.5px;
	}
	.problem .said {
		color: var(--state-stale);
	}
	.prompt input {
		font: inherit;
		margin-left: 6px;
		padding: 2px 6px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		width: 16rem;
		max-width: 100%;
	}
	.row-said {
		color: var(--ink-soft);
	}
	.fix {
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
	}
	.fix:hover:not(:disabled) {
		text-decoration: underline;
	}
	.fix:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
	.fix.danger {
		color: var(--state-stale);
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.from,
	.nope {
		color: var(--ink-faint);
	}
	.from {
		margin-left: 0.3em;
	}
	.pending {
		margin-left: 6px;
		font-family: var(--sans);
		font-size: 10.5px;
		font-weight: 600;
		padding: 1px 7px;
		border-radius: var(--rad-pill);
		background: var(--ann-suggestion-wash);
		color: var(--ann-suggestion);
		text-decoration: none;
	}
	.acts {
		width: 2em;
		text-align: right;
	}
</style>
