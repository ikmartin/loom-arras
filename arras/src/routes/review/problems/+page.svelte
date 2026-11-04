<script lang="ts">
	// Review › Problems: what is wrong in the person's files first, open and counted; an agent's copy's, the cited works' and every remark below, each folded and said to be whose it is. Each problem is titled by what is wrong, opens at its place, and offers its fixes: one a viewer can do as a button, any other as a command to copy. The filters stand in the page; the severity and a code live in the URL, so a link can open it showing one of them.
	import { page } from '$app/state';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { Diagnostic, Fix } from '$lib/manifest/types';
	import { byWork, groupProblems, lineUrl, openUrl, partsOf, splitFixes, titleOf, type Group } from '$lib/diagnostics';
	import { copyText } from '$lib/clipboard';
	import { keyTarget, placeUrl, workUrl } from '$lib/nav';
	import { route } from '$lib/paths';
	import { setQuery } from '$lib/query';
	import { jobs } from '$lib/jobs.svelte';
	import { bibText } from '$lib/works';
	import { can, write } from '$lib/write';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';

	const m = $derived(store.manifest!);
	const SEVERITIES = ['error', 'warning', 'info'] as const;
	const NAMES: Record<string, [string, string]> = { error: ['error', 'errors'], warning: ['warning', 'warnings'], info: ['remark', 'remarks'] };
	const severity = $derived((SEVERITIES as readonly string[]).includes(page.url.searchParams.get('severity') ?? '') ? page.url.searchParams.get('severity')! : '');
	const code = $derived(page.url.searchParams.get('code') ?? '');
	let search = $state('');
	const words = $derived(search.trim().toLowerCase());
	const matches = (d: Diagnostic) => (!severity || d.severity === severity) && (!code || d.code === code) && (!words || `${titleOf(d)} ${d.message} ${d.code}`.toLowerCase().includes(words));
	const all = $derived(partsOf(m.diagnostics));
	const parts = $derived(partsOf(m.diagnostics.filter(matches)));
	const filtered = $derived(!!(severity || code || words));
	const counts = $derived(Object.fromEntries(SEVERITIES.map((s) => [s, m.diagnostics.filter((d) => d.severity === s).length])));
	const works = $derived(byWork(m, parts.works));
	const pick = (v: string) => void setQuery(page.url, 'severity', severity === v ? '' : v);
	// what the person opened or folded, kept across the manifest drawn again after an act
	let folds = $state<Record<string, boolean>>({});
	const isOpen = (id: string, fallback: boolean) => folds[id] ?? (fallback || !!code);
	const toggled = (id: string) => (e: Event) => (folds[id] = (e.currentTarget as HTMLDetailsElement).open);

	// the acts this publisher serves; a static build serves none, and every fix is then a command to copy
	let served = $state<Record<string, boolean>>({});
	$effect(() => {
		void Promise.all(['library-update', 'agents-update'].map((e) => can(e))).then(([library, agents]) => (served = { 'library-update': library, 'agents-update': agents }));
	});

	// each act's answer, said beside it until the next act there; a library run's follows the run to its end
	let answers = $state<Record<string, { text: string; refused: boolean; works?: string[] }>>({});
	let busy = $state('');
	function said(id: string): { text: string; refused: boolean } | undefined {
		const a = answers[id];
		const run = a?.works && !a.refused ? jobs.forWorks(a.works) : undefined;
		if (!run || run.state === 'queued' || run.state === 'running') return a;
		if (run.state === 'failed') return { text: run.error ?? 'The library run failed.', refused: true };
		return { text: ['Done.', run.report?.verdict].filter(Boolean).join(' '), refused: false };
	}
	async function act(id: string, fix: Fix): Promise<void> {
		const a = fix.act!;
		busy = id;
		let text = '';
		let refused = false;
		let works: string[] | undefined;
		if (a.endpoint === 'library-update') {
			const b = a.body as { works?: string[]; redo?: boolean; steps?: string[] };
			const done = await jobs.start(b.works ?? [], { redo: !!b.redo, steps: b.steps });
			const named = (b.works ?? []).join(', ') || 'every work';
			works = b.works ?? [];
			if (done.ok) text = `Digesting ${named}${b.redo ? ' again' : ''}; the Library shows the run, and this page is drawn again when it ends.`;
			else [text, refused] = [done.error?.message ?? 'The library run did not start.', true];
		} else {
			const done = await write(a.endpoint, a.body);
			if (done.ok) {
				text = typeof done.result === 'string' ? `Done: ${done.result}.` : 'Done.';
				await store.refresh();
			} else [text, refused] = [done.error?.message ?? 'That was not done.', true];
		}
		answers = { ...answers, [id]: { text, refused, works } };
		busy = '';
	}
	const running = (ck: string) => jobs.forWorks([ck])?.state === 'queued' || jobs.forWorks([ck])?.state === 'running';

	let copied = $state('');
	async function copy(command: string) {
		if (await copyText(command)) {
			copied = command;
			setTimeout(() => (copied = copied === command ? '' : copied), 1600);
		}
	}
	const workTitle = (ck: string) => bibText(m.references[ck]?.bib.title as string) || ck;
	// a cited work's digest-again fix is offered once, beside the work, so its problems do not each repeat it
	const again = (ck: string, f: Fix) => f.act?.endpoint === 'library-update' && (f.act.body as { works?: string[] }).works?.[0] === ck && !!(f.act.body as { redo?: boolean }).redo;
	const workAct = (ck: string, items: Diagnostic[]) => items.flatMap((d) => d.fixes ?? []).find((f) => again(ck, f));
	/** Where a work with no paper can be given one, or asked for no longer: its row in the library, by its key. */
	const inLibrary = (d: Diagnostic) => (d.code.endsWith(':no-readable-copy') && d.keys[0] ? `${route('/library')}?q=${encodeURIComponent(d.keys[0])}` : '');
</script>

{#snippet problem(d: Diagnostic, id: string, ck: string)}
	{@const { acts, commands } = splitFixes(d)}
	{@const open = openUrl(m, d)}
	<li data-testid="problem">
		<span class="message">{d.message}</span>
		<span class="where">
			{#if open}<a class="open" href={open} data-testid="problem-open">Open</a>{/if}
			{#if inLibrary(d)}<a class="open" href={inLibrary(d)} data-testid="problem-library">In the library</a>{/if}
			{#each d.locations as l, j (j)}{#if m.files?.some((f) => f.path === l.file)}<a class="loc" href={lineUrl(m, l.file, l.line)} data-testid="problem-location">{l.file}:{l.line}</a>{:else}<code class="loc">{l.file}:{l.line}</code>{/if}{/each}
			{#if d.keys.length > 1}{#each d.keys as k (k)}{#if keyTarget(m, k)}<a class="key" href={placeUrl(m, k)}>{k}</a>{:else}<code class="key">{k}</code>{/if}{/each}{/if}
		</span>
		{#if acts.some((f) => served[f.act!.endpoint] && !again(ck, f)) || commands.length}
			<ul class="fixes">
				{#each acts.filter((f) => !again(ck, f)) as f, j (j)}
					{#if served[f.act!.endpoint]}
						<li class="act">
							<button class="btn small" disabled={!!busy} onclick={() => act(`${id}:${j}`, f)} data-testid="fix-act">{f.label.replace(/^./, (c) => c.toUpperCase())}</button>
							{#if said(`${id}:${j}`)}<Said text={said(`${id}:${j}`)!.text} refused={said(`${id}:${j}`)!.refused} testid="fix-said" />{/if}
						</li>
					{:else}
						<li><button type="button" class="copy" data-testid="fix" onclick={() => copy(f.command)}>{copied === f.command ? 'copied' : 'copy'}</button><code class="command">{f.command}</code> <span class="muted">{f.label}</span></li>
					{/if}
				{/each}
				{#each commands as f (f.command)}
					<li><button type="button" class="copy" data-testid="fix" onclick={() => copy(f.command)}>{copied === f.command ? 'copied' : 'copy'}</button><code class="command">{f.command}</code> <span class="muted">{f.label}</span></li>
				{/each}
			</ul>
		{/if}
	</li>
{/snippet}

{#snippet groups(items: Diagnostic[], part: string, ck: string)}
	{#each groupProblems(items) as g (g.title)}
		{@render group(g, part, ck)}
	{/each}
{/snippet}

{#snippet group(g: Group, part: string, ck: string)}
	<!-- the person's groups stand open; in a folded part each is folded to its title and count, since a digest's can run to forty -->
	<details class="group sev-{g.severity}" open={isOpen(`${part}:${ck}:${g.title}`, part === 'yours')} ontoggle={toggled(`${part}:${ck}:${g.title}`)} data-testid="problem-group" data-codes={g.codes.join(' ')}>
		<summary><h3><span class="title">{g.title}</span> <span class="n">{g.items.length}</span> {#each g.codes as c (c)}<code class="code">{c}</code>{/each}</h3></summary>
		<ul>
			{#each g.items as d, i (i)}{@render problem(d, `${part}:${ck}:${g.title}:${i}`, ck)}{/each}
		</ul>
	</details>
{/snippet}

<main class="page scrollbar-shown">
	<ReviewHeading title="Problems">{#snippet aside()}<HelpDot label="what the problems page shows" topic="problems" />{/snippet}</ReviewHeading>
	<p class="lead">What is wrong in your files comes first, and is what Review counts. What is wrong in an agent's copy, or in the digests of the papers you cite, is below it, folded, and so are the remarks.</p>
	<div class="filters" data-testid="problem-filters">
		{#each SEVERITIES as s (s)}
			<button class="chip" class:on={severity === s} aria-pressed={severity === s} onclick={() => pick(s)} data-testid="filter-{s}">{counts[s]} {NAMES[s][counts[s] === 1 ? 0 : 1]}</button>
		{/each}
		{#if code}<button class="chip on" aria-pressed="true" onclick={() => void setQuery(page.url, 'code', '')} data-testid="filter-code"><code>{code}</code> ×</button>{/if}
		<input type="search" bind:value={search} placeholder="Find a problem" aria-label="Find a problem" data-testid="problem-search" />
	</div>

	<section class="part yours" data-testid="problems-yours">
		<h2>In your files <span class="n" data-testid="problems-yours-count">{parts.yours.length}</span></h2>
		{#if parts.yours.length}
			{@render groups(parts.yours, 'yours', '')}
		{:else}
			<Empty text={filtered && all.yours.length ? 'None of yours matches these filters.' : 'Nothing is wrong in your files.'} testid="problems-none" />
		{/if}
	</section>

	{#if parts.copy.length}
		<details class="part" open={isOpen('copy', false)} ontoggle={toggled('copy')} data-testid="problems-copy">
			<summary><h2>In an agent's copy <span class="n">{parts.copy.length}</span></h2></summary>
			<p class="whose">The agent's to put right, or to leave out when you take the copy back in <a href={route('/review/proposed')}>Proposed to you</a>.</p>
			{@render groups(parts.copy, 'copy', '')}
		</details>
	{/if}

	{#if parts.works.length}
		<details class="part" open={isOpen('works', false)} ontoggle={toggled('works')} data-testid="problems-works">
			<summary><h2>In cited works <span class="n">{parts.works.length}</span></h2></summary>
			<p class="whose">Problems in the digests of the papers you cite. A digest is loom's reading of a paper, not your writing; digesting the work again mends what the reading got wrong.</p>
			{#each works as w (w.work)}
				{@const f = w.work ? workAct(w.work, w.items) : undefined}
				<div class="work" data-testid="problem-work" data-work={w.work}>
					<h3>
						{#if w.work}<a href={workUrl(w.work)}>{workTitle(w.work)}</a> <code class="code">{w.work}</code>{:else}A cited work{/if}
						<span class="n">{w.items.length}</span>
						{#if f && served['library-update']}
							<button class="btn small" disabled={!!busy || running(w.work)} onclick={() => act(`work:${w.work}`, f)} data-testid="digest-again">{running(w.work) ? 'Digesting…' : 'Digest it again'}</button>
						{/if}
					</h3>
					{#if said(`work:${w.work}`)}<Said text={said(`work:${w.work}`)!.text} refused={said(`work:${w.work}`)!.refused} testid="digest-said" />{/if}
					{#if f && !served['library-update']}
						<ul class="fixes"><li><button type="button" class="copy" data-testid="fix" onclick={() => copy(f.command)}>{copied === f.command ? 'copied' : 'copy'}</button><code class="command">{f.command}</code> <span class="muted">{f.label}</span></li></ul>
					{/if}
					{@render groups(w.items, 'works', w.work)}
				</div>
			{/each}
		</details>
	{/if}

	{#if parts.remarks.length}
		<details class="part" open={isOpen('remarks', false)} ontoggle={toggled('remarks')} data-testid="problems-remarks">
			<summary><h2>Remarks <span class="n">{parts.remarks.length}</span></h2></summary>
			<p class="whose">Things worth knowing that are not wrong.</p>
			{@render groups(parts.remarks, 'remarks', '')}
		</details>
	{/if}

	{#if filtered && !parts.yours.length && !parts.copy.length && !parts.works.length && !parts.remarks.length && m.diagnostics.length}
		<p class="faint" data-testid="problems-unmatched">Nothing anywhere matches these filters.</p>
	{/if}
</main>

<style>
	.lead {
		max-width: var(--measure);
		color: var(--ink-soft);
		font-size: 13px;
		line-height: 1.6;
	}
	.filters {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight);
		margin: var(--gap) 0 var(--gap-wide);
		font-size: 12px;
	}
	.chip {
		font: inherit;
		color: var(--ink-soft);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 1px 9px;
		cursor: pointer;
	}
	.chip:hover {
		color: var(--link);
		border-color: var(--link);
	}
	.chip.on {
		background: var(--link-wash);
		color: var(--link);
		border-color: var(--link);
	}
	.filters input {
		font: inherit;
		min-width: 12em;
		flex: 0 1 18em;
		padding: 2px 8px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		background: var(--leaf);
		color: var(--ink);
	}
	.part {
		margin: 0 0 var(--gap-wide);
	}
	.part h2 {
		display: inline;
		font: 400 18px/1.3 Georgia, serif;
		margin: 0;
	}
	.part.yours h2 {
		display: block;
		margin-bottom: var(--gap-tight);
	}
	details.part > summary {
		cursor: pointer;
		list-style-position: outside;
		margin-left: 1em;
	}
	details.part[open] > summary {
		margin-bottom: var(--gap-tight);
	}
	.n {
		font: 400 12px var(--sans);
		color: var(--ink-faint);
		font-variant-numeric: tabular-nums;
	}
	.whose {
		max-width: var(--measure);
		font-size: 12.5px;
		color: var(--ink-soft);
		margin: 0 0 var(--gap);
	}
	.work {
		margin: 0 0 var(--gap-wide);
		padding-left: var(--gap);
		border-left: 2px solid var(--rule);
	}
	.work h3 {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 6px;
		font-size: 14px;
		font-weight: 600;
		margin: 0 0 var(--gap-tight);
	}
	.group {
		margin: 0 0 var(--gap);
	}
	.group > summary {
		cursor: pointer;
		list-style-position: outside;
		margin-left: 1em;
	}
	.group h3 {
		display: inline;
		font-size: 13.5px;
		font-weight: 600;
		margin: 0;
	}
	.sev-error .title {
		color: var(--state-incomplete);
	}
	.sev-warning .title {
		color: var(--state-stale);
	}
	.code {
		font-family: var(--mono);
		font-size: 10.5px;
		font-weight: 400;
		color: var(--ink-faint);
		margin-left: 4px;
	}
	.group ul {
		margin: 0;
		padding-left: 1.2em;
	}
	.group > ul > li {
		font-size: 12.5px;
		line-height: 1.55;
		margin: 2px 0;
	}
	.where a,
	.where code {
		margin-left: 0.5em;
		font-size: 11.5px;
	}
	.where .loc {
		font-family: var(--mono);
	}
	.fixes {
		list-style: none;
		margin: 2px 0 0;
		padding: 0;
	}
	.fixes li {
		font-size: 11.5px;
		padding: 1px 0;
	}
	.fixes .act {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight);
	}
	.copy {
		font-family: var(--sans);
		font-size: 9px;
		text-transform: uppercase;
		color: var(--ink-faint);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 0 4px;
		margin-right: 4px;
		cursor: pointer;
	}
	.copy:hover {
		color: var(--link);
		border-color: var(--link);
	}
	.command {
		font-family: var(--mono);
	}
</style>
