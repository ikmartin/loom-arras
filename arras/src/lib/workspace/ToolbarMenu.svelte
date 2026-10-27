<script lang="ts">
	// A menu on a pane's toolbar, **view ▾** or **history ▾**: a word with a caret that opens a box of lines (ToolbarItem), moved through with the arrow keys, Home and End, and closed by a line chosen, Escape or a press outside, handing focus back to its word.
	import { tick, type Snippet } from 'svelte';
	import Popover from '$lib/components/Popover.svelte';

	let {
		label,
		name,
		menuName,
		testid,
		menuTestid,
		width = 230,
		divided = false,
		dot = false,
		children
	}: {
		/** The word on the toolbar. */
		label: string;
		/** The accessible name of the word: what it opens, and for what. */
		name: string;
		/** The accessible name of the box of lines. */
		menuName: string;
		testid: string;
		menuTestid: string;
		width?: number;
		/** A rule before the word, when something stands to its left. */
		divided?: boolean;
		/** A mode inside is on. */
		dot?: boolean;
		/** The lines; `[role^="menuitem"]` are the ones the keys move through. */
		children: Snippet;
	} = $props();

	let button = $state<HTMLButtonElement | null>(null);
	let list = $state<HTMLElement | null>(null);
	let open = $state(false);

	function items(): HTMLElement[] {
		return [...(list?.querySelectorAll<HTMLElement>('[role^="menuitem"]') ?? [])];
	}

	/** Close the menu, handing focus back to the word when it was inside, so a keyboard reader is not left on nothing. */
	function close(): void {
		const had = !!list?.contains(document.activeElement);
		open = false;
		if (had) button?.focus();
	}

	async function toggle(): Promise<void> {
		open = !open;
		if (!open) return;
		await tick();
		items()[0]?.focus();
	}

	function keys(e: KeyboardEvent): void {
		const all = items();
		const at = all.indexOf(document.activeElement as HTMLElement);
		const to = e.key === 'ArrowDown' ? at + 1 : e.key === 'ArrowUp' ? at - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? all.length - 1 : null;
		if (to === null || !all.length) return;
		e.preventDefault();
		all[(to + all.length) % all.length].focus();
	}

	// a line chosen closes the menu, after its own handler has run; a greyed one, and one that opens more lines in place, does not
	function chosen(e: MouseEvent): void {
		const it = (e.target as Element).closest('[role^="menuitem"]');
		if (it && it.getAttribute('aria-disabled') !== 'true' && !it.hasAttribute('aria-expanded')) close();
	}
</script>

<Popover bind:open placement="below" align="end" {width} onclose={close}>
	{#snippet trigger()}
		<button type="button" class="word" class:divided aria-haspopup="menu" aria-expanded={open} aria-label={name} data-testid={testid} bind:this={button} onclick={toggle}
			>{label}{#if dot}<span class="dot" aria-hidden="true" data-testid="{testid}-on"></span>{/if}<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"
				><path d="M4.5 6.5 L8 10 L11.5 6.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg
			></button
		>
	{/snippet}
	<!-- svelte-ignore a11y_click_events_have_key_events (a menu item is a button or a link, whose Enter and Space arrive as clicks) -->
	<div class="menu" role="menu" tabindex="-1" aria-label={menuName} data-testid={menuTestid} bind:this={list} onkeydown={keys} onclick={chosen}>
		{@render children()}
	</div>
</Popover>

<style>
	.word {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		margin-left: 2px;
		padding: 2px 8px 2px 9px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
	/* the divider before the word, only when something stands to its left */
	.word.divided {
		border-left: 1px solid var(--rule);
	}
	.word:hover,
	.word[aria-expanded='true'] {
		color: var(--ink);
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--link);
	}
	.word:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: 2px;
		border-radius: 4px;
	}
	.menu {
		padding: 6px 0;
		font-family: var(--sans);
		font-size: 12.5px;
		outline: none;
	}
	.menu :global(hr) {
		border: 0;
		border-top: 1px solid var(--rule);
		margin: 5px 0;
	}
</style>
