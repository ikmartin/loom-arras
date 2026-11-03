<script lang="ts">
	// Review › Library (plan 0.24.4): the proposed results waiting to be verified, one queue across the library (ProposalQueue); the ledger, every work the quilt holds with what the person needs to know and do about it (LibraryRow); and the citation suggestions, each decided where it stands in the list. A row says whether the paper is filed, how much has been read off it and from where, how much the person verified and what waits for them, whether it has an overview and where they cite it, and its problems with their fixes; its ⋯ menu acts on it, and selected rows are acted on together.
	//
	// **The list of works has one home, and it is the left column** (V2): this page is a working table, not a second list to navigate by, so it registers no panel of its own and the panel keeps its Library section beside it. Its search and filters are its own, in its header and the address.
	//
	// The backlog is this page filtered to `proposed` (DR-206). The filters answer "which of these need me", then what each work still lacks, then what a person has vouched for.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { setQuery } from '$lib/query';
	import { reachedExternal } from '$lib/reached';
	import { keepRow, ledgerRows, matches, needsWork, problemsOf, type LedgerFilter, type Problem } from '$lib/library';
	import { displayNode } from '$lib/nodes/display';
	import ProposalQueue from '$lib/review/ProposalQueue.svelte';
	import LibraryRow, { type Caps, type Done, type RowAct } from '$lib/review/LibraryRow.svelte';
	import { can, write } from '$lib/write';
	import { jobs, running } from '$lib/jobs.svelte';
	import { askOverview } from '$lib/notes';
	import NoSession from '$lib/sessions/NoSession.svelte';
	import { writable } from '$lib/sessions/sessions.svelte';
	import JobProgress from '$lib/components/JobProgress.svelte';
	import LibraryRun from '$lib/components/LibraryRun.svelte';
	import NetworkAsk from '$lib/components/NetworkAsk.svelte';
	import AddWork from '$lib/components/AddWork.svelte';

	const m = $derived(store.manifest!);
	const SHOWS: { v: LedgerFilter; label: string }[] = [
		{ v: 'all', label: 'all' },
		{ v: 'needs-you', label: 'needs you' },
		{ v: 'no-paper', label: 'no paper' },
		{ v: 'no-overview', label: 'no overview' },
		{ v: 'not-cited', label: 'not cited' },
		{ v: 'proposed', label: 'proposed' },
		{ v: 'verified', label: 'verified' }
	];
	const asked = $derived(page.url.searchParams.get('show') ?? '');
	const filter = $derived<LedgerFilter>(SHOWS.find((s) => s.v === asked)?.v ?? 'all');
	const q = $derived(page.url.searchParams.get('q') ?? '');
	let typed = $state<string | null>(null);

	// a row's problems: what stands on disk, and what the last run on it could not do while the publisher holds that run
	const problems = $derived.by(() => {
		const out: Record<string, Problem[]> = {};
		for (const ref of Object.values(m.references)) out[ref.citekey] = problemsOf(m, ref, jobs.lastRun(ref.citekey));
		return out;
	});
	const wants = (ck: string, r: Parameters<typeof needsWork>[0]) => needsWork(r) || (problems[ck]?.length ?? 0) > 0;
	const rows = $derived.by(() => {
		const reached = reachedExternal(m);
		// one row per work: a version's counts are its work's, and the row names it; what wants the person first, then by key
		return ledgerRows(m, reached).sort((a, b) => Number(wants(b.citekey, b)) - Number(wants(a.citekey, a)) || a.citekey.localeCompare(b.citekey));
	});
	const found = $derived(rows.filter((r) => matches(r, q)));
	const shown = $derived(found.filter((r) => keepRow(r, problems[r.citekey] ?? [], filter)));
	const count = (v: LedgerFilter) => found.filter((r) => keepRow(r, problems[r.citekey] ?? [], v)).length;
	const show = (v: string) => void setQuery(page.url, 'show', v, 'all');
	let searchTimer: ReturnType<typeof setTimeout> | null = null;
	function search(value: string): void {
		typed = value;
		if (searchTimer) clearTimeout(searchTimer);
		searchTimer = setTimeout(() => void setQuery(page.url, 'q', value.trim()), 200);
	}

	// what the publisher serves, asked once
	let caps = $state<Caps>({ runs: false, upload: false, ask: false, ignore: false, remove: false });
	let canAdd = $state(false);
	let cites = $state(false);
	onMount(() => {
		void Promise.all(['library-update', 'library-file', 'note', 'library-ignore', 'library-remove', 'library-add', 'library-cite'].map((e) => can(e))).then(([runs, upload, ask, ignore, remove, add, cite]) => {
			caps = { runs, upload, ask, ignore, remove };
			canAdd = add;
			cites = cite;
			if (runs) jobs.ask();
		});
	});
	const selecting = $derived(caps.runs || caps.ask);

	// rows picked for the acts on several works at once, by key; a row filtered out stays picked, and the bar says how many
	let picked = $state<Set<string>>(new Set());
	const toggle = (ck: string) => {
		const next = new Set(picked);
		if (!next.delete(ck)) next.add(ck);
		picked = next;
	};
	const allShown = $derived(shown.length > 0 && shown.every((r) => picked.has(r.citekey)));
	const toggleAll = () => (picked = allShown ? new Set([...picked].filter((ck) => !shown.some((r) => r.citekey === ck))) : new Set([...picked, ...shown.map((r) => r.citekey)]));
	let bulkSaid = $state('');

	// runs started here: one network question for the whole page, and each run's progress under the header until dismissed
	const online = $derived(m.config?.library.online === true);
	let question = $state<((allow: boolean | null) => void) | null>(null);
	let seen = $state<string[]>([]);
	$effect(() => {
		for (const j of jobs.list) if (running(j) && !seen.includes(j.id)) seen = [j.id, ...seen];
	});
	const watched = $derived(seen.map((id) => jobs.list.find((j) => j.id === id)).filter((j) => !!j));

	/** Start a run over `works`, asking first for the network where one of them lacks a paper or a source and the quilt has it off. */
	function runOn(works: string[], redo: boolean): Promise<Done> {
		const lacking = works.some((ck) => !m.references[ck]?.artifacts?.pdf || !m.references[ck]?.artifacts?.source);
		const start = async (allow: boolean): Promise<Done> => {
			const answer = await jobs.start(works, { online: allow, redo });
			return answer.ok ? { ok: true, said: '' } : { ok: false, said: answer.error?.message ?? 'The run could not start' };
		};
		if (online || !lacking) return start(false);
		return new Promise((resolve) => {
			question = (allow) => {
				question = null;
				resolve(allow === null ? { ok: false, said: '' } : start(allow));
			};
		});
	}

	let uploading = $state<string | null>(null);
	let uploadOpen = $state(false);
	let adding = $state(false);

	/** What a row's act does: a run, an upload, a note asking for the overview, a claim about its paper, or taking it out. */
	async function onact(ck: string, act: RowAct, why?: string): Promise<Done> {
		if (act === 'run' || act === 'redo') return runOn([ck], act === 'redo');
		if (act === 'upload') {
			uploading = ck;
			uploadOpen = true;
			return { ok: true, said: '' };
		}
		if (act === 'ask') {
			const refused = await askOverview(ck);
			return { ok: !refused, said: refused || 'Asked an agent for its overview' };
		}
		const answer =
			act === 'remove' ? await write('library-remove', { citekey: ck }) : await write('library-ignore', { citekey: ck, why: why ?? '', undo: act === 'unignore' });
		if (!answer.ok) return { ok: false, said: answer.error?.message ?? 'The publisher refused it' };
		await store.refresh();
		return { ok: true, said: String(answer.result ?? '') };
	}

	async function runPicked(): Promise<void> {
		const done = await runOn([...picked], false);
		bulkSaid = done.said;
		if (done.ok) picked = new Set();
	}
	async function askPicked(): Promise<void> {
		const want = [...picked].filter((ck) => !m.references[ck]?.overview);
		let asked = 0;
		for (const ck of want) {
			const refused = await askOverview(ck);
			if (refused) return void (bulkSaid = refused);
			asked += 1;
		}
		bulkSaid = want.length ? `Asked an agent for ${asked} overview${asked === 1 ? '' : 's'}` : 'Every selected work has an overview';
	}

	// a citation suggestion is an agent's annotation proposing a work for a place in the text; it is decided here, or where it stands, which its link opens
	const citations = $derived(Object.values(m.annotations ?? {}).filter((a) => a.kind === 'citation' && !a.in_reply_to && !a.discarded && a.status === 'open'));
	const why = $derived(writable(m));
	let citeSaid = $state('');
	async function decide(id: string, decision: 'accept' | 'reject'): Promise<void> {
		const answer = await write('library-cite', { annotation: id, decision });
		citeSaid = answer.ok ? '' : (answer.error?.message ?? 'The publisher refused it');
		if (answer.ok) await store.refresh();
	}
</script>

<main class="page">
	<ProposalQueue />
	<header class="head">
		<h1>Library</h1>
		<input class="search" type="search" placeholder="Search title, author or key" value={typed ?? q} oninput={(e) => search(e.currentTarget.value)} aria-label="Search the library" data-testid="ledger-search" />
		{#if caps.runs || canAdd}
			<div class="everything">
				{#if canAdd}<button class="add" onclick={() => (adding = true)} data-testid="review-add">+ Add a work</button>{/if}
				{#if caps.runs}<LibraryRun works={[]} label="Fetch and digest everything" look="button" test="run-everything" />{/if}
			</div>
		{/if}
	</header>
	<p class="filters" role="group" aria-label="which works">
		{#each SHOWS as s (s.v)}
			<button class="count" class:on={filter === s.v} aria-pressed={filter === s.v} onclick={() => show(s.v)} data-testid="show-{s.v}">{s.label} <span class="n">{count(s.v)}</span></button>
		{/each}
	</p>
	{#if question}<NetworkAsk onallow={() => question?.(true)} onoffline={() => question?.(false)} oncancel={() => question?.(null)} />{/if}
	{#each watched as j (j.id)}
		<JobProgress job={j} ondismiss={() => (seen = seen.filter((id) => id !== j.id))} />
	{/each}
	{#if selecting}
		<!-- always in its place, so a row picked does not move the rows under the pointer -->
		<div class="bulk" class:idle={!picked.size} role="group" aria-label="the selected works" data-testid="bulk">
			{#if picked.size}
				<span>{picked.size} selected</span>
				{#if caps.runs}<button class="add" onclick={() => void runPicked()} data-testid="bulk-run">Fetch and digest selected</button>{/if}
				{#if caps.ask}<button class="add" disabled={!!why} title={why || undefined} onclick={() => void askPicked()} data-testid="bulk-ask">Ask an agent for overviews</button>{/if}
				<button class="as-link" onclick={() => ((picked = new Set()), (bulkSaid = ''))} data-testid="bulk-clear">Clear</button>
			{:else}
				<span>Select works to act on several at once.</span>
			{/if}
			{#if bulkSaid}<span class="said" role="status" data-testid="bulk-said">{bulkSaid}</span>{/if}
		</div>
	{/if}
	<table class="list" data-testid="library-works">
		<thead>
			<tr>
				{#if selecting}<th class="pick"><input type="checkbox" checked={allShown} onchange={toggleAll} aria-label="Select every work shown" data-testid="select-all" /></th>{/if}
				<th>work</th>
				<th title="A copy of the paper is filed in loom's store">paper</th>
				<th class="num" title="Results read off the paper, and from where: its LaTeX source, or its pages">digest</th>
				<th class="num" title="Results you compared with the paper and vouched for, and those an agent proposed that wait for you">verified</th>
				<th title="The overview an agent or you wrote: what it proves, what is new, the hardest part">overview</th>
				<th class="num" title="How many places in your documents cite it">cited</th>
				<th aria-label="what to do with each work"></th>
			</tr>
		</thead>
		<tbody>
			{#each shown as r (r.citekey)}
				<LibraryRow row={r} ref={m.references[r.citekey]} problems={problems[r.citekey] ?? []} {caps} select={selecting} checked={picked.has(r.citekey)} ontoggle={() => toggle(r.citekey)} onact={(act, why) => onact(r.citekey, act, why)} />
			{/each}
		</tbody>
	</table>
	{#if !shown.length}
		<p class="muted">Nothing here. {#if filter !== 'all' || q}<button class="as-link" onclick={() => void setQuery(new URL(page.url.pathname, page.url), 'show', '')}>Show every work</button>{/if}</p>
	{/if}
	{#if citations.length}
		<section class="citations" data-testid="citation-suggestions">
			<h2>Citation suggestions <span class="n">{citations.length}</span></h2>
			{#if cites && why}<p class="muted"><NoSession /></p>{/if}
			<ul>
				{#each citations as a (a.id)}
					<li>
						<a href={`quilt:${a.id}`}>{displayNode(m, a.target.key).name}</a>{#if a.payload} <span class="muted">· {a.payload.slice(0, 80)}</span>{/if}
						{#if cites}
							<span class="decide">
								<button class="as-link" disabled={!!why} title={why || undefined} onclick={() => void decide(a.id, 'accept')} data-testid="cite-accept-{a.id}">accept</button>
								<button class="as-link" disabled={!!why} title={why || undefined} onclick={() => void decide(a.id, 'reject')} data-testid="cite-reject-{a.id}">reject</button>
							</span>
						{/if}
					</li>
				{/each}
			</ul>
			{#if citeSaid}<p class="said" role="alert">{citeSaid}</p>{/if}
		</section>
	{/if}
</main>

{#if canAdd}<AddWork bind:open={adding} />{/if}
{#if caps.upload && uploading}<AddWork bind:open={uploadOpen} work={uploading} />{/if}

<style>
	/* The page's own header, on one line: the table is the first screen (V1). */
	.head {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: var(--gap);
		margin-bottom: var(--gap-tight);
	}
	.head h1 {
		margin: 0;
	}
	.search {
		font: inherit;
		font-family: var(--sans);
		font-size: 12.5px;
		padding: 4px 10px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		background: var(--sheet);
		color: var(--ink);
		width: 16rem;
		max-width: 100%;
	}
	.add {
		font: inherit;
		font-size: 12.5px;
		padding: 4px 12px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--sheet);
		color: var(--ink);
		cursor: pointer;
	}
	.add:hover:not(:disabled) {
		background: var(--link-wash);
	}
	.add:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
	.everything {
		margin-left: auto;
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		justify-content: flex-end;
		max-width: 28rem;
	}
	.filters {
		display: flex;
		flex-wrap: wrap;
		gap: 4px var(--gap);
		margin: 0 0 var(--gap);
		font-family: var(--sans);
		font-size: 12px;
	}
	.n {
		color: var(--ink-faint);
		font-variant-numeric: tabular-nums;
	}
	button.count {
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		color: var(--ink-soft);
		cursor: pointer;
	}
	button.count.on {
		color: var(--ink);
		font-weight: 600;
	}
	.bulk {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		/* one height whether its buttons show or not: a row picked must not move the rows under the pointer */
		min-height: 40px;
		box-sizing: border-box;
		padding: 4px 10px;
		margin-bottom: var(--gap-tight);
		background: var(--link-wash);
		border-radius: var(--rad-control);
		font-family: var(--sans);
		font-size: 12.5px;
	}
	.bulk.idle {
		background: none;
		color: var(--ink-faint);
	}
	.said {
		font-family: var(--sans);
		font-size: 12px;
		color: var(--ink-soft);
	}
	th.num {
		text-align: right;
	}
	.pick {
		width: 1.5em;
	}
	.citations {
		margin-top: var(--gap-wide);
	}
	.citations h2 {
		font-size: 1rem;
	}
	.decide {
		margin-left: 8px;
		font-family: var(--sans);
		font-size: 12px;
	}
	.decide button + button {
		margin-left: 6px;
	}
</style>
