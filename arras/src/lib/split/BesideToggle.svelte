<script lang="ts">
	// The control that opens and closes the split, on its own so a view can put it where its own controls live rather
	// than take the band `Beside` draws above itself. The state is the URL's, so two of these on one page would agree.
	//
	// It says the same thing in every view: the reader learns one name for the arrangement rather than one per page.
	import { page } from '$app/state';
	import { setQuery } from '$lib/query';

	let { open = false }: { open?: boolean } = $props();

	const on = $derived((page.url.searchParams.get('beside') ?? (open ? '1' : '0')) === '1');
</script>

<button
	type="button"
	class="as-link"
	aria-pressed={on}
	data-testid="beside-toggle"
	onclick={() => setQuery(page.url, 'beside', on ? '0' : '1', open ? '1' : '0')}>{on ? 'close split' : 'open split'}</button
>
