<script lang="ts">
	// Which file the viewer opens on and which document loom uses by default, edited as a draft until Save; the research state's path shown and never written, since moving it means moving the page.
	import { store } from '$lib/manifest/client.svelte';
	import type { QuiltSettings } from '$lib/manifest/types';
	import { isAux } from '../aux';
	import { draft } from './draft.svelte';
	import Row from './Row.svelte';

	let { config, editable }: { config: QuiltSettings; editable: boolean } = $props();
	const text = (key: string) => String(draft.value(key) ?? '');
	const m = $derived(store.manifest!);
	// a front door is any file the viewer opens as itself: a `.tex` file that is no document opens the one that reads it, and LaTeX's own files are no door
	const doors = $derived((m.files ?? []).filter((f) => f.kind !== 'tex' && !isAux(f.path)).map((f) => f.path));
	const unsetDoor = $derived((m.files ?? []).some((f) => f.path === 'README.md') ? 'README.md' : 'the default document');
	// the person's own documents: an agent's copy or draft is never the default
	const documents = $derived(m.masters.filter((d) => !d.copy_of && !d.scope).map((d) => d.path));
	const withCurrent = (list: string[], current: string) => (current && !list.includes(current) ? [current, ...list] : list);
</script>

<div class="card">
	<Row id="quilt.home" refused={draft.refused['quilt.home']}>
		<select value={text('quilt.home')} disabled={!editable} aria-label="Front door" onchange={(e) => draft.set('quilt.home', e.currentTarget.value)} data-testid="config-quilt.home">
			<option value="">Unset: {unsetDoor}</option>
			{#each withCurrent(doors, text('quilt.home')) as path (path)}<option value={path}>{path}{doors.includes(path) ? '' : ' (not shown)'}</option>{/each}
		</select>
	</Row>
	<Row id="quilt.main" refused={draft.refused['quilt.main']}>
		<select value={text('quilt.main')} disabled={!editable} aria-label="Default document" onchange={(e) => draft.set('quilt.main', e.currentTarget.value)} data-testid="config-quilt.main">
			<option value="">Unset{documents.length === 1 ? `: ${documents[0]}` : ''}</option>
			{#each withCurrent(documents, text('quilt.main')) as path (path)}<option value={path}>{path}{documents.includes(path) ? '' : ' (not a document)'}</option>{/each}
		</select>
	</Row>
	<Row id="quilt.research_state">
		<span class="fixed">{config.quilt.research_state}</span>
	</Row>
</div>
<p class="aside">The research state's path is changed in config.toml, and the page moved with it.</p>
