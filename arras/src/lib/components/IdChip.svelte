<script lang="ts">
	// A node's id, and its aliases behind a tooltip (book 15.3.2).
	let { id, aliases = [] }: { id: string; aliases?: string[] } = $props();
</script>

<span class="id" title={aliases.length ? 'also ' + aliases.join(', ') : undefined}>{id}{#if aliases.length}<span class="more">+{aliases.length}</span>{/if}</span>

<style>
	.id {
		font-family: var(--mono);
		font-size: 9px;
		color: var(--ink-faint);
		letter-spacing: 0.02em;
	}
	.more {
		margin-left: 2px;
		color: var(--link);
	}
</style>
