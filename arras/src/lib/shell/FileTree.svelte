<script lang="ts">
	// Docs as the project's tree (plan 0.22.7): the person's directories and the files the viewer shows, each directory folding as an explorer's does. A document opens as itself, with the agent's copies of it beneath its row; the research state opens as the page it is, where it lives; an included `.tex` file opens the document that reads it, at its place (V7); every other file opens as a file. Which directories are open is the reader's, kept per quilt in this browser; the ones holding a live document start open, and the one holding what is being read opens when it is read.
	import { store } from '$lib/manifest/client.svelte';
	import type { Master, ProjectFile } from '$lib/manifest/types';
	import { masterUrl } from '$lib/nav';
	import { route } from '$lib/paths';
	import { itemForFile, pathFor } from '$lib/workspace/item';
	import { documentLabel } from '$lib/workspace/names';
	import { workspace } from '$lib/workspace/store.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { isAux } from './aux';

	let { files, masters, own, copiesOf, section }: { files: ProjectFile[]; masters: Master[]; own: Master[]; copiesOf: (path: string) => Master[]; section: (m: Master) => string } = $props();

	interface Dir {
		name: string;
		path: string;
		dirs: Dir[];
		files: ProjectFile[];
	}

	const KEY = 'arras.tree';
	const m = $derived(store.manifest!);
	const corpus = $derived(m.corpus.name);
	const statePath = $derived(m.research_state?.path ?? '');

	/** The directories and files as a tree, each level's directories first and every name in the order a person sorts them. */
	const root = $derived.by(() => {
		const top: Dir = { name: '', path: '', dirs: [], files: [] };
		const at = new Map<string, Dir>([['', top]]);
		const dirOf = (path: string): Dir => {
			const known = at.get(path);
			if (known) return known;
			const cut = path.lastIndexOf('/');
			const d: Dir = { name: path.slice(cut + 1), path, dirs: [], files: [] };
			dirOf(cut < 0 ? '' : path.slice(0, cut)).dirs.push(d);
			at.set(path, d);
			return d;
		};
		// LaTeX's auxiliary files are left out unless the reader asked for them (Settings)
		for (const f of prefs.hideAux ? files.filter((x) => !isAux(x.path)) : files) {
			const cut = f.path.lastIndexOf('/');
			dirOf(cut < 0 ? '' : f.path.slice(0, cut)).files.push(f);
		}
		const byName = (a: { name?: string; path: string }, b: { name?: string; path: string }) =>
			(a.name ?? a.path).localeCompare(b.name ?? b.path, undefined, { sensitivity: 'base', numeric: true });
		const sort = (d: Dir) => {
			d.dirs.sort(byName);
			d.files.sort((a, b) => name(a.path).localeCompare(name(b.path), undefined, { sensitivity: 'base', numeric: true }));
			d.dirs.forEach(sort);
		};
		sort(top);
		return top;
	});

	function name(path: string): string {
		return path.slice(path.lastIndexOf('/') + 1);
	}
	function ancestors(path: string): string[] {
		const parts = path.split('/').slice(0, -1);
		return parts.map((_, i) => parts.slice(0, i + 1).join('/'));
	}

	/** What is being read, as a path in the tree: a document's, a file's, the research state's. */
	const reading = $derived.by(() => {
		const c = workspace.onScreen ? workspace.current : null;
		if (!c) return '';
		if (c.kind === 'document' || c.kind === 'file') return c.id;
		if (c.kind === 'page' && c.id === 'state') return statePath;
		return '';
	});

	let toggled = $state<Record<string, boolean>>({});
	$effect(() => {
		const name = corpus;
		try {
			toggled = (JSON.parse(globalThis.localStorage?.getItem(KEY) ?? '{}') as Record<string, Record<string, boolean>>)[name] ?? {};
		} catch {
			toggled = {};
		}
	});
	function save(): void {
		try {
			const all = JSON.parse(globalThis.localStorage?.getItem(KEY) ?? '{}') as Record<string, Record<string, boolean>>;
			all[corpus] = toggled;
			globalThis.localStorage?.setItem(KEY, JSON.stringify(all));
		} catch {
			// a browser that stores nothing still folds for this visit
		}
	}
	// what is read is shown: a directory closed earlier opens when something in it is opened
	$effect(() => {
		const shut = ancestors(reading).filter((d) => toggled[d] === false);
		if (!shut.length) return;
		toggled = { ...toggled, ...Object.fromEntries(shut.map((d) => [d, true])) };
		save();
	});
	const startsOpen = $derived(new Set([...own.flatMap((o) => ancestors(o.path)), ...ancestors(reading)]));
	const open = (dir: string) => toggled[dir] ?? startsOpen.has(dir);
	function toggle(dir: string): void {
		toggled = { ...toggled, [dir]: !open(dir) };
		save();
	}

	const ownPaths = $derived(new Set(own.map((o) => o.path)));
	function href(f: ProjectFile): string {
		if (f.path === statePath) return route('/page/state');
		if (f.kind === 'document') return masterUrl(f.path);
		return pathFor(m, itemForFile(m, f.path));
	}
</script>

{#snippet link(d: Master)}
	{@const here = reading === d.path}
	<a href={masterUrl(d.path)} class:here aria-current={here ? 'page' : undefined}>{documentLabel(masters, d.path)}{#if section(d)}<span class="aside">{section(d)}</span>{/if}</a>
{/snippet}

{#snippet level(d: Dir)}
	{#each d.dirs as sub (sub.path)}
		<li class="dir" data-testid="docs-dir" data-path={sub.path}>
			<button class="fold" aria-expanded={open(sub.path)} onclick={() => toggle(sub.path)}>{open(sub.path) ? '▾' : '▸'} {sub.name}</button>
			{#if open(sub.path)}
				<ul class="plain docs level">{@render level(sub)}</ul>
			{/if}
		</li>
	{/each}
	{#each d.files as f (f.path)}
		{@const here = reading === f.path}
		{@const copies = f.kind === 'document' ? copiesOf(f.path) : []}
		{#if f.path === statePath}
			<li data-testid="docs-state" class="file state">
				<a href={href(f)} class:here aria-current={here ? 'page' : undefined} title={f.path}>Research state</a>
			</li>
		{:else}
			<li class="file" class:document={f.kind === 'document'} class:live={ownPaths.has(f.path)} data-kind={f.kind} data-testid="docs-file">
				<a href={href(f)} class:here aria-current={here ? 'page' : undefined} title={f.path}>{name(f.path)}</a>
				{#if copies.length}
					<!-- the agent's copies of this document, which the person and an agent both edit -->
					<ul class="plain docs copies" data-testid="docs-copies">
						{#each copies as c (c.path)}<li>{@render link(c)}</li>{/each}
					</ul>
				{/if}
			</li>
		{/if}
	{/each}
{/snippet}

<ul class="plain docs tree" data-testid="docs-tree">{@render level(root)}</ul>

<style>
	.tree :global(a) {
		overflow-wrap: anywhere;
	}
	.level {
		margin: 0 0 0 0.55rem;
		padding-left: 0.5rem;
		border-left: 1px solid var(--rule);
	}
	.fold {
		all: unset;
		cursor: pointer;
		color: var(--ink-soft);
		font: inherit;
	}
	.fold:hover,
	.fold:focus-visible {
		color: var(--ink);
	}
	.file:not(.document):not(.state) > a {
		color: var(--ink-soft);
	}
	.file[data-kind='tex'] > a {
		color: var(--ink-faint);
	}
	.docs a.here {
		color: var(--ink);
		font-weight: 600;
	}
	.docs.copies {
		margin: 0 0 0 0.55rem;
		padding-left: 0.5rem;
		border-left: 1px solid var(--rule);
	}
	.aside {
		margin-left: 0.4em;
		color: var(--ink-faint);
		font-size: 0.9em;
	}
</style>
