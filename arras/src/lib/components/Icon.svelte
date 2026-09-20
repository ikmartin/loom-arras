<script lang="ts">
	// The icon strip's glyphs (book 15.2.3). Line icons rather than the unicode marks the strip carried before: `◇ ▤ ◈ ✓ ! ¶` render at whatever weight and baseline a font decides, so they sat unevenly and read as punctuation. These are drawn on one 24x24 grid at one stroke width, which is what makes a column of them look like a set.
	//
	// Inline rather than an icon package: arras ships vendored inside loom's wheel, so a dependency is weight in every install, and six paths are a few hundred bytes.
	let { name, size = 19 }: { name: string; size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.75"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
	focusable="false"
>
	{#if name === 'home'}
		<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
		<path d="M9 22V12h6v10" />
	{:else if name === 'read'}
		<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
		<path d="M14 2v6h6" />
		<path d="M16 13H8" />
		<path d="M16 17H8" />
		<path d="M10 9H8" />
	{:else if name === 'graph'}
		<circle cx="18" cy="5" r="3" />
		<circle cx="6" cy="12" r="3" />
		<circle cx="18" cy="19" r="3" />
		<path d="m8.59 13.51 6.83 3.98" />
		<path d="m15.41 6.51-6.82 3.98" />
	{:else if name === 'review'}
		<path d="m3 17 2 2 4-4" />
		<path d="m3 7 2 2 4-4" />
		<path d="M13 6h8" />
		<path d="M13 12h8" />
		<path d="M13 18h8" />
	{:else if name === 'problems'}
		<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
		<path d="M12 9v4" />
		<path d="M12 17h.01" />
	{:else if name === 'digest'}
		<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H16l4 4v9" />
		<path d="M16 2v4h4" />
		<circle cx="11" cy="16" r="4" />
		<path d="m20 22-2.5-2.5" />
	{:else if name === 'references'}
		<path d="m16 6 4 14" />
		<path d="M12 6v14" />
		<path d="M8 8v12" />
		<path d="M4 4v16" />
	{:else if name === 'search'}
		<circle cx="11" cy="11" r="8" />
		<path d="m21 21-4.3-4.3" />
	{:else if name === 'expand'}
		<path d="M15 3h6v6" />
		<path d="M9 21H3v-6" />
		<path d="m21 3-7 7" />
		<path d="m3 21 7-7" />
	{:else if name === 'close'}
		<path d="M18 6 6 18" />
		<path d="m6 6 12 12" />
	{/if}
</svg>

<style>
	svg {
		display: block;
	}
</style>
