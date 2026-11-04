<script lang="ts" module>
	/** One change as the list shows it: its name, where it stands in words and as a state (`undecided`, `taken`, `left`, `clash`, `note`), and the words the find field also matches. */
	export interface ListedChange {
		key: string;
		name: string;
		says: string;
		state: string;
		section?: string;
		also?: string;
	}
</script>

<script lang="ts">
	// Where a review is among a copy's or a pull's changes, and the way to any of them: the counter ("2 of 7") opens the whole list beside it, grouped by section, each change with a dot for where it stands, and with a field to find one by name. ‹ and › beside it step one at a time; the list stays out of the way of the two texts being compared until it is asked for.
	import Popover from '$lib/components/Popover.svelte';

	let { changes, active, onpick, findable = false }: { changes: ListedChange[]; active: string; onpick: (key: string) => void; findable?: boolean } = $props();

	let open = $state(false);
	let filter = $state('');
	const at = $derived(Math.max(0, changes.findIndex((c) => c.key === active)));
	const shown = $derived(filter.trim() ? changes.filter((c) => `${c.name} ${c.section ?? ''} ${c.also ?? ''}`.toLowerCase().includes(filter.trim().toLowerCase())) : changes);
	// the sections in the order they first come, each heading every change under it
	const groups = $derived.by(() => {
		const out: { section: string; rows: ListedChange[] }[] = [];
		for (const c of shown) {
			const g = out.find((x) => x.section === (c.section ?? ''));
			if (g) g.rows.push(c);
			else out.push({ section: c.section ?? '', rows: [c] });
		}
		return out;
	});
	function pick(key: string): void {
		onpick(key);
		open = false;
		filter = '';
	}
</script>

<Popover bind:open placement="below" width={360} label="Every change" testid="change-list" onclose={() => (filter = '')}>
	{#snippet trigger({ open, toggle })}
		<button type="button" class="at" aria-expanded={open} aria-haspopup="dialog" title="Every change" data-testid="change-at" onclick={toggle}>{changes.length ? at + 1 : 0} of {changes.length}<span class="chev" aria-hidden="true"></span></button>
	{/snippet}
	<div class="list">
		{#if findable}
			<!-- svelte-ignore a11y_autofocus -->
			<input class="find" type="search" placeholder="find a change" aria-label="Find a change" bind:value={filter} autofocus data-testid="change-filter" />
		{/if}
		{#each groups as g (g.section + g.rows[0].key)}
			{#if g.section}<p class="group">{g.section}</p>{/if}
			{#each g.rows as c (c.key)}
				<button type="button" class="row" class:active={c.key === active} onclick={() => pick(c.key)} data-testid="change-row" data-key={c.key} data-state={c.state}>
					<span class="dot s-{c.state}" aria-hidden="true"></span><span class="name">{c.name}</span><small>{c.says}</small>
				</button>
			{/each}
		{:else}
			<p class="none">No change matches.</p>
		{/each}
	</div>
</Popover>

<style>
	.at {
		font: inherit;
		font-size: 12.5px;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 3px 10px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		background: var(--sheet);
		color: var(--ink);
		cursor: pointer;
		white-space: nowrap;
	}
	.at:hover,
	.at[aria-expanded='true'] {
		border-color: var(--rule-strong);
	}
	.chev {
		width: 5px;
		height: 5px;
		border-right: 1.5px solid var(--ink-faint);
		border-bottom: 1.5px solid var(--ink-faint);
		transform: translateY(-2px) rotate(45deg);
	}
	.list {
		padding: 8px;
		font-family: var(--sans);
		font-size: 13px;
	}
	.find {
		width: 100%;
		box-sizing: border-box;
		margin-bottom: 4px;
		font: inherit;
		padding: 5px 9px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		background: var(--sheet);
	}
	.group {
		margin: 8px 6px 2px;
		font-size: 11.5px;
		color: var(--ink-soft);
	}
	.row {
		all: unset;
		box-sizing: border-box;
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 5px 6px;
		border-radius: var(--rad-control);
		cursor: pointer;
	}
	.row:hover {
		background: var(--leaf);
	}
	.row.active {
		background: var(--link-wash);
	}
	.row .name {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.row small {
		flex: none;
		font-size: 11.5px;
		color: var(--ink-faint);
	}
	.row[data-state='taken'] small {
		color: var(--state-accepted);
	}
	.row[data-state='clash'] small {
		color: var(--state-stale);
	}
	/* where it stands: hollow to decide, filled once taken, grey once left out, amber where it cannot be taken */
	.dot {
		flex: none;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		box-shadow: inset 0 0 0 1.5px var(--ink-soft);
	}
	.dot.s-taken {
		background: var(--state-accepted);
		box-shadow: none;
	}
	.dot.s-left {
		background: var(--ink-faint);
		box-shadow: none;
	}
	.dot.s-clash {
		background: var(--state-stale);
		box-shadow: none;
	}
	.dot.s-note {
		box-shadow: inset 0 0 0 1.5px var(--ink-faint);
	}
	.none {
		margin: 6px;
		color: var(--ink-soft);
	}
</style>
