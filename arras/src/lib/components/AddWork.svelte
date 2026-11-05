<script lang="ts">
	// Adding a work to the library by hand (plan 0.24.2): paste an identifier or a BibTeX entry, or drop a PDF. What is pasted is recognised as you type; an entry is read at once, and an identifier is looked up on "Look up", asking first for the network where the quilt has it off. The answer says what was found, the key it would take, whether loom can digest it, and which works in the library may already be it. Adding writes it into loom's bibliography and, unless unticked, fetches and digests it; the work's Info then opens on the run.
	//
	// A dropped PDF is kept whatever is known about it. Its metadata is filled in where it can be guessed and the person may correct it; Add writes it, and where the PDF plainly is a work the library holds already, Add files it there, unless the person says it is another. No question about the network stands in its way: a lookup runs only where the network is already allowed. The filing answers at once; reading its text is a run, whose progress its Info shows.
	//
	// Given a `work`, it is the upload of that work's PDF alone (plan 0.24.4): the PDF is filed under it as soon as it is read, on the person's word, and the dialog closes where it was opened, unless there is something to say about the filing.
	import { goto } from '$app/navigation';
	import Popover from '$lib/components/Popover.svelte';
	import { jobs } from '$lib/jobs.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { workUrl } from '$lib/nav';
	import { write } from '$lib/write';
	import NetworkAsk from './NetworkAsk.svelte';

	let { open = $bindable(false), work = '' }: { open?: boolean; work?: string } = $props();

	interface Found {
		state: 'found' | 'missing' | 'unreachable' | 'offline' | 'cannot';
		kind: string;
		label: string;
		value: string;
		entry: Record<string, string>;
		key: string;
		digest: 'source' | 'lookup' | '';
		duplicates: string[];
		message: string;
	}
	interface Seen {
		upload: string;
		name: string;
		best: string;
		held: boolean;
		weak: string;
		nearest: string;
		matches: { citekey: string }[];
		offer?: Record<string, string>;
		key?: string;
		digest?: string;
		duplicates?: string[];
	}

	/** About what a browser can encode; `loom library add` takes any size. */
	const MAX_MB = 256;
	let text = $state('');
	let kind = $state<{ kind: string; label: string; value: string } | null>(null);
	let found = $state<Found | null>(null);
	let seen = $state<Seen | null>(null);
	/** The new work's entry as the person has it, starting from what the PDF gave. */
	let title = $state('');
	let author = $state('');
	let year = $state('');
	/** The person says this PDF is not the work it looks like, so it is added as its own. */
	let apart = $state(false);
	/** What there is to say about a filing that is done, which keeps the dialog open: where it went and why. */
	let notice = $state<{ citekey: string; text: string } | null>(null);
	let digestNow = $state(true);
	let busy = $state('');
	let error = $state('');
	let hover = $state(false);
	/** The person allowed the network for what this dialog does now; a later act carries it. */
	let allowed = $state(false);
	/** A question waiting on the person: which act it gates, and what to do with the answer. */
	let asking = $state<{ question: string; allow: string; offline?: string; go: (allow: boolean | null) => void } | null>(null);

	const online = $derived(store.manifest?.config?.library.online === true);
	const refs = $derived(store.manifest?.references ?? {});
	const lookable = $derived(!!kind && ['doi', 'arxiv', 'zbl'].includes(kind.kind));
	/** Works in the library this PDF may be after all, each a button: those it names equally, and those with its identifier or its title. */
	const maybe = $derived(seen && !seen.best ? [...new Set([...seen.matches.map((m) => m.citekey), ...(seen.duplicates ?? [])])] : []);
	/** Whether Add has something to add: a work looked up, or a PDF. */
	const ready = $derived(!!seen || found?.state === 'found');

	function reset(): void {
		text = '';
		kind = found = seen = notice = null;
		title = author = year = '';
		apart = false;
		busy = error = '';
		allowed = false;
		asking = null;
	}

	// what the text is, said as you type, from the publisher, which alone decides
	let timer: ReturnType<typeof setTimeout> | null = null;
	$effect(() => {
		const now = text;
		found = null;
		error = '';
		// what was pressed last is what Add adds: a pasted identifier takes over from a dropped PDF
		if (now.trim()) seen = null;
		if (timer) clearTimeout(timer);
		if (!now.trim()) {
			kind = null;
			return;
		}
		timer = setTimeout(async () => {
			const answer = (await write('library-recognise', { text: now })) as { ok: boolean; kind?: string; label?: string; value?: string };
			if (text !== now || !answer.ok) return;
			kind = { kind: answer.kind!, label: answer.label!, value: answer.value! };
			// an entry is what it says: no network, so it is read at once
			if (answer.kind === 'bibtex') void lookUp(false);
		}, 250);
	});

	async function lookUp(allow: boolean): Promise<void> {
		busy = 'Looking it up…';
		const answer = (await write('library-lookup', { text, online: allow })) as { ok: boolean; found?: Found; error?: { message: string } };
		busy = '';
		if (answer.ok) found = answer.found!;
		else error = answer.error?.message ?? 'Could not look it up';
	}
	function pressLookUp(): void {
		if (online || allowed) return void lookUp(allowed);
		asking = {
			question: 'Looking this up needs the network, which this quilt has off. Allow it for this lookup, and for fetching what it finds?',
			allow: 'Allow and look up',
			go: (allow) => {
				asking = null;
				if (allow) {
					allowed = true;
					void lookUp(true);
				}
			}
		};
	}

	/** Run `act`, first asking for the network where fetching wants it and nobody has allowed it. */
	function withNetwork(act: (allow: boolean) => Promise<void>): void {
		if (!digestNow || online || allowed) return void act(allowed);
		asking = {
			question: 'Fetching and digesting it needs the network, which this quilt has off. Allow it for this run?',
			allow: 'Allow and add',
			offline: 'Add, run offline',
			go: (allow) => {
				asking = null;
				if (allow !== null) void act(allow);
			}
		};
	}

	async function done(citekey: string): Promise<void> {
		await store.refresh();
		void jobs.refresh();
		open = false;
		reset();
		// Info, where the run shows, though the work may now have a paper to open on; an upload for a work stays where it was asked
		if (!work) await goto(workUrl(citekey) + '?view=info');
	}

	function press(): void {
		if (seen) void fileUnder(seen.best && !apart ? seen.best : '');
		else add();
	}

	function add(): void {
		withNetwork(async (allow) => {
			busy = 'Adding…';
			const answer = (await write('library-add', { text, fetch: digestNow, online: allow })) as { ok: boolean; citekey?: string; error?: { message: string } };
			busy = '';
			if (answer.ok) await done(answer.citekey!);
			else error = answer.error?.message ?? 'Could not add it';
		});
	}

	async function upload(file: File | undefined): Promise<void> {
		if (!file) return;
		error = '';
		seen = notice = found = kind = null;
		text = '';
		apart = false;
		if (file.size > MAX_MB * 1024 * 1024) return void (error = `${file.name} is larger than the ${MAX_MB} MB the viewer can carry; loom library add FILE on the command line takes it`);
		busy = `Reading ${file.name}…`;
		const data = await new Promise<string>((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
			reader.onerror = () => reject(reader.error);
			reader.readAsDataURL(file);
		}).catch(() => '');
		const answer = (await write('library-upload', { name: file.name, data, online: online || allowed })) as Seen & { ok: boolean; error?: { message: string } };
		busy = '';
		if (!answer.ok) return void (error = answer.error?.message ?? `Could not read ${file.name}`);
		seen = answer;
		title = answer.offer?.title ?? '';
		author = answer.offer?.author ?? '';
		year = answer.offer?.year ?? '';
		if (work) void fileUnder(work);
	}

	/** File the upload under `citekey`, or as a new work for ''. The network is never asked for here: a lookup or a fetch runs only where it is allowed already, and Info can run one later. */
	async function fileUnder(citekey: string): Promise<void> {
		const s = seen!;
		const allow = online || allowed;
		busy = 'Filing it…';
		const entry = s.offer ? { entry: { title, author, year } } : {};
		const body = citekey ? { upload: s.upload, citekey, fetch: digestNow && allow, online: allow } : { upload: s.upload, new: true, ...entry, fetch: digestNow && allow, online: allow };
		const answer = (await write('library-file', body)) as { ok: boolean; citekey?: string; note?: string; already?: string; unmapped?: string; error?: { message: string } };
		busy = '';
		if (!answer.ok) return void (error = answer.error?.message ?? 'Could not file it');
		const said = [answer.already ? `${s.name}: ${answer.already}.` : '', answer.note ? `Filed under ${answer.citekey}, on your word, though ${answer.note}.` : '', answer.unmapped ? `It has no page text (${answer.unmapped}), so nothing can search or quote its pages; the PDF itself opens as usual.` : ''].filter(Boolean).join(' ');
		if (!said) return void (await done(answer.citekey!));
		await store.refresh();
		notice = { citekey: answer.citekey!, text: said };
	}

	const who = (entry: Record<string, string>) => (entry.author ?? '').split(/\s+and\s+/).filter(Boolean).join('; ');
	const titleOf = (ck: string) => String(refs[ck]?.bib?.title ?? ck);
</script>

{#snippet card(entry: Record<string, string>, key: string, digest: string, dups: string[])}
	<div class="found" data-testid="add-found">
		<p class="t">{entry.title}</p>
		<p class="who">{who(entry)}{entry.year ? ` · ${entry.year}` : ''}{entry.journal || entry.publisher ? ` · ${entry.journal || entry.publisher}` : ''}</p>
		<ul>
			{#if digest === 'source'}<li class="can">The paper and its LaTeX source can be fetched from arXiv, and loom reads its results off the source.</li>
			{:else}<li class="cannot">Loom will look for an arXiv copy by its title; failing that, drop its PDF here, and an agent proposes its results from the pages.</li>{/if}
			<li>It would be filed as <code data-testid="add-key">{key}</code>.</li>
			{#each dups as d (d)}<li class="cannot" data-testid="add-duplicate">The library already holds <a href={workUrl(d)}>{titleOf(d)}</a> (<code>{d}</code>), which may be this work or another version of it.</li>{/each}
		</ul>
	</div>
{/snippet}

<Popover modal bind:open label="Add a work" testid="add-work" onclose={reset}>
	<div class="dlg">
		<header>
			<h2>{work ? `Upload a PDF of ${work}` : 'Add a work to the library'}</h2>
			<button class="close" aria-label="Close" onclick={() => (open = false)}>×</button>
		</header>
		{#if work}
			<p class="lead">Drop a PDF of <strong>{titleOf(work)}</strong>: loom keeps a copy of it as <code>{work}</code>'s document.</p>
		{:else}
		<p class="lead">Paste a DOI, an arXiv id or link, a zbMATH number, or a whole BibTeX entry; or drop a PDF. It goes into loom's own bibliography, beside what your documents cite.</p>
		<textarea bind:value={text} placeholder={'10.1007/…   or   arXiv:0805.2065   or   @article{…}'} aria-label="An identifier or a BibTeX entry" data-testid="add-text"></textarea>
		<div class="det" aria-live="polite">
			{#if kind}
				<span class="kind" class:unknown={kind.kind === 'unknown'} data-testid="add-kind">{kind.label}</span>
				{#if kind.value && kind.kind !== 'bibtex'}<code>{kind.value}</code>{/if}
				{#if lookable}<button class="btn small" onclick={pressLookUp} disabled={!!busy} data-testid="add-look-up">Look up</button>{/if}
				{#if kind.kind === 'isbn' || kind.kind === 'mr'}<span class="note">Loom has no service to look this up: paste its DOI, its arXiv id or its BibTeX entry instead.</span>{/if}
				{#if kind.kind === 'unknown'}<span class="note">Paste a DOI, an arXiv id, a zbMATH number or a BibTeX entry.</span>{/if}
			{/if}
		</div>
		{#if asking}<NetworkAsk question={asking.question} allow={asking.allow} offline={asking.offline} onallow={() => asking?.go(true)} onoffline={asking.offline ? () => asking?.go(false) : undefined} oncancel={() => asking?.go(null)} />{/if}
		{#if found}
			{#if found.state === 'found'}{@render card(found.entry, found.key, found.digest, found.duplicates)}
			{:else}
				<div class="found bad" role="alert" data-testid="add-not-found" data-state={found.state}>
					<strong>{found.state === 'missing' ? 'Not found.' : found.state === 'unreachable' ? 'Could not ask.' : 'Not looked up.'}</strong>
					{found.message}
					{#if found.state === 'unreachable'}<button class="btn small" onclick={() => void lookUp(allowed)}>Try again</button>{/if}
				</div>
			{/if}
		{/if}
		{/if}
		<label
			class="drop"
			class:hover
			ondragover={(e) => {
				e.preventDefault();
				hover = true;
			}}
			ondragleave={() => (hover = false)}
			ondrop={(e) => {
				e.preventDefault();
				hover = false;
				void upload(e.dataTransfer?.files?.[0]);
			}}
			data-testid="add-drop"
		>
			<input type="file" accept="application/pdf,.pdf" onchange={(e) => void upload(e.currentTarget.files?.[0])} data-testid="add-file" />
			{#if seen}<strong data-testid="add-chosen">{seen.name}</strong>, or drop another.{:else if work}Drop the PDF here, or <u>choose it</u>.{:else}Drop a PDF here, or <u>choose one</u>.{/if}
		</label>
		{#if notice}
			<div class="found" data-testid="add-notice">{notice.text}</div>
		{:else if seen && !work}
			{#if seen.held}
				<div class="found" data-testid="add-matches">
					<p>This PDF is already in the library, as <a href={workUrl(seen.best)}>{titleOf(seen.best)}</a> (<code>{seen.best}</code>).</p>
				</div>
			{:else if seen.best && !apart}
				<div class="found" data-testid="add-matches">
					<p>This is <a href={workUrl(seen.best)}>{titleOf(seen.best)}</a> (<code>{seen.best}</code>), which the library has. Add files this PDF under it.</p>
					<button class="plain" onclick={() => (apart = true)} data-testid="add-different">It is a different work</button>
				</div>
			{:else if seen.offer}
				<div class="meta" data-testid="add-metadata">
					<p class="meta-head">Metadata:</p>
					<label class="field">Title <input bind:value={title} data-testid="add-title" /></label>
					<label class="field">Author <input bind:value={author} data-testid="add-author" /></label>
					<label class="field">Year <input bind:value={year} data-testid="add-year" /></label>
					{#each maybe as d (d)}<p class="maybe" data-testid="add-duplicate">The library has <a href={workUrl(d)}>{titleOf(d)}</a> (<code>{d}</code>), which may be this work. <button class="plain" onclick={() => void fileUnder(d)} disabled={!!busy} data-testid="add-file-under">File it there instead</button></p>{/each}
				</div>
			{/if}
		{/if}
		{#if error}<p class="error" role="alert" data-testid="add-error">{error}</p>{/if}
		<footer>
			{#if !seen && !work}<label class="opt"><input type="checkbox" bind:checked={digestNow} data-testid="add-fetch" /> Fetch and digest it now</label>
			{:else if !notice && (online || allowed)}<label class="opt"><input type="checkbox" bind:checked={digestNow} data-testid="add-fetch" /> Look it up and digest it now</label>
			{:else}<span class="opt"></span>{/if}
			{#if busy}<span class="busy">{busy}</span>{/if}
			{#if notice}
				<button class="btn primary" onclick={() => void done(notice!.citekey)} data-testid="add-done">Done</button>
			{:else}
				<button class="btn" onclick={() => (open = false)}>Cancel</button>
				{#if !work && !seen?.held}<button class="btn primary" disabled={!ready || !!busy} onclick={press} data-testid="add-add">Add</button>{/if}
			{/if}
		</footer>
	</div>
</Popover>

<style>
	.dlg {
		width: min(620px, calc(100vw - 2 * var(--gap)));
		max-height: calc(100dvh - 2 * var(--gap));
		overflow-y: auto;
		padding: 20px 22px;
		font-family: var(--sans);
		font-size: 13px;
		color: var(--ink);
		background: var(--sheet);
		box-sizing: border-box;
	}
	header {
		display: flex;
		align-items: center;
	}
	h2 {
		margin: 0;
		font-size: 17px;
		font-weight: 600;
	}
	.close {
		margin-left: auto;
		border: 0;
		background: none;
		font-size: 18px;
		color: var(--ink-faint);
		cursor: pointer;
	}
	.lead {
		margin: 4px 0 14px;
		color: var(--ink-soft);
		font-size: 12.5px;
	}
	textarea {
		width: 100%;
		height: 76px;
		box-sizing: border-box;
		font-family: var(--mono);
		font-size: 12px;
		padding: 8px 10px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--sheet);
		color: var(--ink);
		resize: vertical;
	}
	.det {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin: 8px 0;
		min-height: 24px;
		font-size: 12px;
		color: var(--ink-soft);
	}
	.kind {
		font-size: 11px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 9px;
		background: var(--link-wash);
		color: var(--link);
	}
	.kind.unknown {
		background: var(--leaf);
		color: var(--ink-faint);
	}
	.note {
		color: var(--ink-soft);
	}
	code {
		font-family: var(--mono);
		font-size: 0.92em;
	}
	.found {
		margin: 12px 0 0;
		border: 1px solid var(--rule);
		border-radius: 10px;
		padding: 12px 14px;
		font-size: 12.5px;
	}
	.found p {
		margin: 0 0 6px;
	}
	.found .t {
		font-family: var(--serif);
		font-size: 15px;
		margin: 0;
	}
	.found .who {
		color: var(--ink-soft);
		margin: 2px 0 8px;
	}
	.found ul {
		margin: 0;
		padding-left: 18px;
		color: var(--ink-soft);
	}
	.found li {
		margin: 2px 0;
	}
	.found .can {
		color: var(--state-accepted);
	}
	.found .cannot {
		color: var(--state-stale);
	}
	.found.bad {
		border-color: var(--state-conflicted);
		color: var(--state-conflicted);
	}
	.meta {
		margin: 12px 0 0;
		font-size: 12.5px;
	}
	.meta-head {
		margin: 0 0 8px;
		font-weight: 600;
	}
	.maybe {
		margin: 8px 0 0;
		color: var(--ink-soft);
	}
	.plain {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		color: var(--link);
		cursor: pointer;
	}
	.plain:hover:not(:disabled) {
		text-decoration: underline;
	}
	.field {
		display: grid;
		grid-template-columns: 52px 1fr;
		align-items: center;
		gap: 8px;
		margin: 0 0 6px;
		color: var(--ink-soft);
	}
	.field input {
		font: inherit;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 6px;
		padding: 3px 7px;
		min-width: 0;
	}
	.drop {
		display: block;
		margin: 14px 0 0;
		border: 1.5px dashed var(--rule-strong);
		border-radius: 10px;
		padding: 14px;
		text-align: center;
		color: var(--ink-soft);
		font-size: 12.5px;
		cursor: pointer;
	}
	.drop.hover {
		background: var(--link-wash);
		border-color: var(--link);
	}
	.drop input {
		position: absolute;
		width: 1px;
		height: 1px;
		opacity: 0;
	}
	.error {
		color: var(--state-conflicted);
		margin: 10px 0 0;
	}
	footer {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 16px;
	}
	.opt {
		margin-right: auto;
		display: flex;
		align-items: center;
		gap: 6px;
		color: var(--ink-soft);
		font-size: 12px;
	}
	.busy {
		color: var(--ink-faint);
		font-size: 12px;
	}
	.btn {
		font: inherit;
		font-size: 12.5px;
		padding: 5px 12px;
		border-radius: 8px;
		border: 1px solid var(--rule);
		background: var(--sheet);
		color: var(--ink);
		cursor: pointer;
	}
	.btn:hover:not(:disabled) {
		background: var(--link-wash);
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.btn.small {
		padding: 2px 9px;
		font-size: 12px;
	}
	.btn.primary {
		background: var(--ink);
		color: var(--sheet);
		border-color: var(--ink);
	}
	.found .plain {
		margin-top: 2px;
	}
</style>
