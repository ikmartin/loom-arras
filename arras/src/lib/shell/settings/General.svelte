<script lang="ts">
	// The quilt's name, id prefix and TeX engine, edited as a draft until Save; the history folder shown and never written, since moving it means moving what it holds.
	import type { QuiltSettings } from '$lib/manifest/types';
	import { draft } from './draft.svelte';
	import Row from './Row.svelte';

	let { config, editable }: { config: QuiltSettings; editable: boolean } = $props();
	const ENGINES = ['pdflatex', 'xelatex', 'lualatex', 'latex'];
	const text = (key: string) => String(draft.value(key) ?? '');
</script>

<div class="card">
	<Row id="quilt.name" refused={draft.refused['quilt.name']}>
		<input class="text" value={text('quilt.name')} disabled={!editable} aria-label="Name" oninput={(e) => draft.set('quilt.name', e.currentTarget.value)} data-testid="config-quilt.name" />
	</Row>
	<Row id="quilt.prefix" refused={draft.refused['quilt.prefix']}>
		<input class="text mono short" value={text('quilt.prefix')} disabled={!editable} aria-label="Id prefix" oninput={(e) => draft.set('quilt.prefix', e.currentTarget.value)} data-testid="config-quilt.prefix" />
	</Row>
	<Row id="quilt.engine" refused={draft.refused['quilt.engine']}>
		<select value={text('quilt.engine')} disabled={!editable} aria-label="TeX engine" onchange={(e) => draft.set('quilt.engine', e.currentTarget.value)} data-testid="config-quilt.engine">
			{#each ENGINES.includes(text('quilt.engine')) ? ENGINES : [text('quilt.engine'), ...ENGINES] as engine (engine)}<option value={engine}>{engine}</option>{/each}
		</select>
	</Row>
</div>
<h3>Advanced</h3>
<div class="card">
	<Row id="quilt.history">
		<span class="fixed">{config.quilt.history}</span>
	</Row>
</div>
<p class="aside">The history folder is changed in config.toml, and its files moved with it.</p>
