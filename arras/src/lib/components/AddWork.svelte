<script lang="ts">
	// Adding a work to the library by hand (plan 0.24.2): paste an identifier or a BibTeX entry, or drop a PDF. What is pasted is recognised as you type; an entry is read at once, and an identifier is looked up on "Look up", asking first for the network where the quilt has it off. The answer says what was found, the key it would take, whether loom can digest it, and which works in the library may already be it. Adding writes it into loom's bibliography and, unless unticked, fetches and digests it; the work's Info then opens on the run.
	//
	// Given a `work`, it is the upload of that work's PDF alone (plan 0.24.4): the PDF is filed under it as soon as it is read, where the publisher finds the document is that work, and the dialog closes where it was opened; a refusal says why, and the dialog stays.
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
		weak: string;
		offer?: Record<string, string>;
		key?: string;
		digest?: string;
		duplicates?: string[];
	}

	const MAX = 64 * 1024 * 1024;
	let text = $state('');
	let kind = $state<{ kind: string; label: string; value: string } | null>(null);
	let found = $state<Found | null>(null);
	let seen = $state<Seen | null>(null);
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

	function reset(): void {
		text = '';
		kind = found = seen = null;
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
		seen = null;
		if (file.size > MAX) return void (error = `${file.name} is larger than 64 MB`);
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
		if (work) fileUnder(work);
	}

	function file(isNew: boolean): void {
		fileUnder(isNew ? '' : seen!.best);
	}

	/** File the upload under `citekey`, or as a new work for ''. */
	function fileUnder(citekey: string): void {
		const s = seen!;
		withNetwork(async (allow) => {
			busy = 'Filing it…';
			const body = citekey ? { upload: s.upload, citekey, fetch: digestNow, online: allow } : { upload: s.upload, new: true, fetch: digestNow, online: allow };
			const answer = (await write('library-file', body)) as { ok: boolean; citekey?: string; error?: { message: string } };
			busy = '';
			if (answer.ok) await done(answer.citekey!);
			else error = answer.error?.message ?? 'Could not file it';
		});
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
			<p class="lead">Drop a PDF of <strong>{titleOf(work)}</strong>: loom files it under <code>{work}</code> where its first pages show it is that work.</p>
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
			{#if work}Drop the PDF here, or <u>choose it</u>.{:else}Drop a PDF here, or <u>choose one</u>: loom files it under the work it shows it is, or offers a new entry from its first pages.{/if}
		</label>
		{#if seen && !work}
			{#if seen.best}
				<div class="found" data-testid="add-matches">
					<p><strong>{seen.name}</strong> is <a href={workUrl(seen.best)}>{titleOf(seen.best)}</a> (<code>{seen.best}</code>).</p>
					<button class="btn" onclick={() => file(false)} disabled={!!busy} data-testid="add-file-there">File it there</button>
				</div>
			{:else if seen.offer && seen.offer.title}
				<p class="said">No work in the library matches <strong>{seen.name}</strong>. From its first pages:</p>
				{@render card(seen.offer, seen.key ?? '', seen.digest ?? 'lookup', seen.duplicates ?? [])}
				<button class="btn" onclick={() => file(true)} disabled={!!busy} data-testid="add-file-new">Add it as a new work</button>
			{:else}
				<div class="found bad" role="alert" data-testid="add-unread">
					No work in the library matches <strong>{seen.name}</strong>{seen.weak ? `: ${seen.weak}` : ''}, and its pages give no title loom trusts. Paste its DOI, arXiv id or BibTeX entry to add the work, then drop the PDF again.
				</div>
			{/if}
		{/if}
		{#if error}<p class="error" role="alert" data-testid="add-error">{error}</p>{/if}
		<footer>
			<label class="opt"><input type="checkbox" bind:checked={digestNow} data-testid="add-fetch" /> Fetch and digest it now</label>
			{#if busy}<span class="busy">{busy}</span>{/if}
			<button class="btn" onclick={() => (open = false)}>Cancel</button>
			{#if !work}<button class="btn primary" disabled={found?.state !== 'found' || !!busy} onclick={add} data-testid="add-add">Add</button>{/if}
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
	.said {
		margin: 12px 0 0;
		font-size: 12.5px;
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
	.found .btn,
	.said + .found + .btn,
	.btn[data-testid='add-file-new'] {
		margin-top: 8px;
	}
</style>
