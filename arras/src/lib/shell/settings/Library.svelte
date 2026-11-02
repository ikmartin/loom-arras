<script lang="ts">
	// Whether the library may use the network, and the address the lookup services are given; a draft until Save.
	import { draft } from './draft.svelte';
	import Row from './Row.svelte';
	import Toggle from './Toggle.svelte';

	let { editable }: { editable: boolean } = $props();
</script>

<div class="card">
	<Row id="library.online" refused={draft.refused['library.online']}>
		<Toggle label="Use the network" test="config-library.online" disabled={!editable} checked={draft.value('library.online') === true} set={(on) => draft.set('library.online', on)} />
	</Row>
	<Row id="library.contact" refused={draft.refused['library.contact']}>
		<input class="text" type="email" placeholder="you@example.org" value={String(draft.value('library.contact') ?? '')} disabled={!editable} aria-label="Contact address" oninput={(e) => draft.set('library.contact', e.currentTarget.value)} data-testid="config-library.contact" />
	</Row>
</div>
