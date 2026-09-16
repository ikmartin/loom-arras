<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<title>arras</title>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children()}
