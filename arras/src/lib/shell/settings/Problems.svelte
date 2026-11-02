<script lang="ts">
	// The problems this quilt silences, and a choice of the ones that can be, those reported now first; a draft until Save.
	import { store } from '$lib/manifest/client.svelte';
	import type { QuiltSettings } from '$lib/manifest/types';
	import { draft } from './draft.svelte';
	import Chips from './Chips.svelte';
	import Row from './Row.svelte';

	let { config, editable }: { config: QuiltSettings; editable: boolean } = $props();
	const silenced = $derived((draft.value('lint.disable') as string[] | undefined) ?? []);
	const reported = $derived(new Set((store.manifest?.diagnostics ?? []).map((d) => d.code)));
	const open = $derived(config.lint.codes.filter((c) => !silenced.includes(c)));
	const now = $derived(open.filter((c) => reported.has(c)));
	const rest = $derived(open.filter((c) => !reported.has(c)));
	let chosen = $state('');
	function silence(): void {
		if (!chosen) return;
		draft.set('lint.disable', [...silenced, chosen]);
		chosen = '';
	}
</script>

<div class="card">
	<Row id="lint.disable" stack refused={draft.refused['lint.disable']}>
		<Chips test="config-lint.disable" items={silenced} remove={editable ? (code) => draft.set('lint.disable', silenced.filter((c) => c !== code)) : undefined} />
		{#if editable}
			<div class="add">
				<select bind:value={chosen} aria-label="A problem to silence" data-testid="silence-choice">
					<option value="">Choose a problem to silence…</option>
					{#if now.length}<optgroup label="Reported now">{#each now as code (code)}<option value={code}>{code}</option>{/each}</optgroup>{/if}
					{#if rest.length}<optgroup label="Others">{#each rest as code (code)}<option value={code}>{code}</option>{/each}</optgroup>{/if}
				</select>
				<button class="btn" disabled={!chosen} onclick={silence} data-testid="silence">Silence</button>
			</div>
		{:else if !silenced.length}
			<p class="aside">Nothing is silenced.</p>
		{/if}
	</Row>
</div>
