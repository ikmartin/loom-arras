<script lang="ts">
	// Review › Library, also reached from the Library shelf under Docs: the ledger, every work the quilt holds with what the person needs to know and do about it (LibraryRow). A row says whether the paper is filed, how much has been read off it and from where, how much the person verified and what waits for them, whether it has an overview and where they cite it, and its problems with their fixes; its ⋯ menu acts on it, and selected rows are acted on together, deleting them among it.
	//
	// **The list of works has one home, and it is the Library shelf under Docs** (V2): this page is a working table, not a second list to navigate by, so it registers no panel of its own. Its search and filters are its own, in its header and the address.
	//
	// The backlog is this page filtered to `proposed` (DR-206). The filters answer "which of these need me", then what each work still lacks, then what a person has vouched for.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { setQuery } from '$lib/query';
	import { reachedExternal } from '$lib/reached';
	import { keepRow, ledgerRows, matches, needsWork, problemsOf, type LedgerFilter, type Problem } from '$lib/library';
	import LibraryRow, { type Caps, type Done, type RowAct } from '$lib/review/LibraryRow.svelte';
	import { can, write } from '$lib/write';
	import { jobs, running } from '$lib/jobs.svelte';
	import { askOverview } from '$lib/notes';
	import { writable } from '$lib/sessions/sessions.svelte';
	import JobProgress from '$lib/components/JobProgress.svelte';
	import LibraryRun from '$lib/components/LibraryRun.svelte';
	import NetworkAsk from '$lib/components/NetworkAsk.svelte';
	import AddWork from '$lib/components/AddWork.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';

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
	let caps = $state<Caps>({ runs: false, upload: false, ask: false, ignore: false, delete: false });
	let canAdd = $state(false);
	onMount(() => {
		void Promise.all(['library-update', 'library-file', 'note', 'library-ignore', 'library-delete', 'library-add'].map((e) => can(e))).then(([runs, upload, ask, ignore, del, add]) => {
			caps = { runs, upload, ask, ignore, delete: del };
			canAdd = add;
			if (runs) jobs.ask();
		});
	});
	const selecting = $derived(caps.runs || caps.ask || caps.delete);

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
	/** The question before deleting what is selected. */
	let deleting = $state(false);

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

	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

	/** Delete one work, or one copy of it: a row deleted has nowhere to say so, so the bar above the table does. */
	async function del(ck: string): Promise<Done> {
		const answer = await write('library-delete', { citekey: ck });
		if (!answer.ok) return { ok: false, said: answer.error?.message ?? 'The publisher refused it' };
		const next = new Set(picked);
		next.delete(ck);
		picked = next;
		await store.refresh();
		return { ok: true, said: capital(String(answer.result ?? '')) };
	}

	/** What a row's act does: a run, an upload, a note asking for the overview, a claim about its paper, or deleting it, or the copy `why` names. */
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
		if (act === 'delete') {
			const done = await del(why ?? ck);
			if (done.ok) bulkSaid = done.said;
			return done;
		}
		const answer = await write('library-ignore', { citekey: ck, why: why ?? '', undo: act === 'unignore' });
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

	/** Delete what is selected, one work at a time, saying what stayed and why. */
	async function deletePicked(): Promise<void> {
		deleting = false;
		bulkSaid = 'Deleting…';
		const refused: string[] = [];
		let gone = 0;
		for (const ck of [...picked]) {
			const done = await del(ck);
			if (done.ok) gone += 1;
			else refused.push(done.said);
		}
		bulkSaid = [gone ? `Deleted ${gone} work${gone === 1 ? '' : 's'}.` : '', ...refused.map((r) => capital(r) + '.')].filter(Boolean).join(' ');
	}

	const why = $derived(writable(m));
</script>

<main class="page scrollbar-shown">
	<ReviewHeading title="Library">{#snippet aside()}
		<input class="search" type="search" placeholder="Search title, author or key" value={typed ?? q} oninput={(e) => search(e.currentTarget.value)} aria-label="Search the library" data-testid="ledger-search" />
		{#if caps.runs || canAdd}
			<div class="everything">
				{#if canAdd}<button class="add" onclick={() => (adding = true)} data-testid="review-add">+ Add a work</button>{/if}
				{#if caps.runs}<LibraryRun works={[]} label="Fetch and digest everything" look="button" test="run-everything" />{/if}
			</div>
		{/if}
	{/snippet}</ReviewHeading>
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
				{#if caps.delete}<button class="add" onclick={() => (deleting = true)} data-testid="bulk-delete">Delete selected</button>{/if}
				<button class="as-link" onclick={() => ((picked = new Set()), (bulkSaid = ''), (deleting = false))} data-testid="bulk-clear">Clear</button>
			{:else}
				<span>Select works to act on several at once.</span>
			{/if}
			{#if bulkSaid}<span class="said" role="status" data-testid="bulk-said">{bulkSaid}</span>{/if}
			{#if deleting && picked.size}
				<p class="asking" data-testid="bulk-delete-ask">
					Delete {picked.size === 1 ? 'this work' : `these ${picked.size} works`} from the library, with loom's copy of each PDF and everything read from it? This cannot be undone.
					<button class="add danger" onclick={() => void deletePicked()} data-testid="bulk-delete-go">Delete</button>
					<button class="as-link" onclick={() => (deleting = false)}>Cancel</button>
				</p>
			{/if}
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
</main>

{#if canAdd}<AddWork bind:open={adding} />{/if}
{#if caps.upload && uploading}<AddWork bind:open={uploadOpen} work={uploading} />{/if}

<style>
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
	/* the header on one line: the table is the first screen (V1) */
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
	.asking {
		flex-basis: 100%;
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 6px 8px;
	}
	.add.danger {
		color: var(--state-stale);
		border-color: var(--state-stale);
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
</style>
