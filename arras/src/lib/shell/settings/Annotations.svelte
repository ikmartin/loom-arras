<script lang="ts">
	// Settings › Annotations: the quilt's annotation types, one at a time, the list at the left and the chosen one at the right: its name, its look with a sample, whether it stays open until resolved or only informs, whether it is listed in Notes, its instructions for agents, and the modes that use it. A draft until Save, which writes the types file whole through `types-save`; Restore defaults writes loom's defaults. Deleting a type a mode uses asks first. A type started from a format menu or a popup (Add new…, Save as new type) is taken by what started it once it is saved. What a type says is only its own name and instructions.
	import { untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { AnnotationType, Look } from '$lib/manifest/types';
	import { write } from '$lib/write';
	import LookControls from '$lib/review/LookControls.svelte';
	import Sample from '$lib/review/Sample.svelte';
	import { hand } from '$lib/review/annotating.svelte';
	import { edit } from '$lib/review/history.svelte';
	import { settingsAsked, type Taker } from './opener.svelte';

	let { editable = false }: { editable?: boolean } = $props();

	/** A type as the draft holds it: an id once loom has given it one. */
	interface Draft {
		id?: string;
		name: string;
		look: Look;
		open: boolean;
		notes: boolean;
		instructions: string;
		modes: string[];
		/** Which draft row this is, kept across renames. */
		key: number;
	}

	let keys = 0;
	const fromQuilt = (types: AnnotationType[]): Draft[] => types.map((t) => ({ id: t.id, name: t.name, look: { ...t.look }, open: t.open, notes: t.notes, instructions: t.instructions, modes: [...(t.modes ?? [])], key: ++keys }));
	/** What Save sends, and what tells a changed draft from the quilt's types. */
	const payload = (list: Draft[]) => list.map((t) => ({ ...(t.id ? { id: t.id } : {}), name: t.name.trim(), color: t.look.color, style: t.look.style, weight: t.look.weight, opacity: t.look.opacity, open: t.open, notes: t.notes, instructions: t.instructions }));

	const quilt = $derived(store.manifest?.annotation_types ?? []);
	let draft = $state<Draft[]>([]);
	let chosen = $state(0);
	let confirming = $state<number | null>(null);
	let busy = $state(false);
	let said = $state('');
	let nameField = $state<HTMLInputElement | null>(null);

	/** The quilt's types as the draft was taken from them. */
	let base = $state('');
	const dirty = $derived(base !== '' && JSON.stringify(payload(draft)) !== base);
	// the draft follows the quilt's types while nothing is changed in it, so a save or an agent's edit of the file shows here
	let seen = '';
	$effect(() => {
		const now = JSON.stringify(quilt);
		if (now === seen) return;
		seen = now;
		if (untrack(() => dirty)) return;
		take();
	});
	function take(): void {
		const at = draft[chosen]?.id;
		draft = fromQuilt(quilt);
		base = JSON.stringify(payload(draft));
		chosen = Math.max(0, draft.findIndex((t) => t.id === at));
	}
	/** The new type a format menu or a popup started, by its draft row, and who takes it once saved. */
	let taking: { key: number; take: Taker } | null = null;
	// Add new… or Save as new type opens this section with a new type started, in the look it was asked with
	$effect(() => {
		const asked = settingsAsked.add;
		if (!asked || !editable) return;
		settingsAsked.add = null;
		untrack(() => {
			add(asked.look);
			if (asked.take) taking = { key: draft[draft.length - 1].key, take: asked.take };
		});
	});

	const current = $derived<Draft | undefined>(draft[chosen]);

	function add(look: Look = { color: 'green', style: 'highlight', weight: 2, opacity: 50 }): void {
		draft.push({ name: '', look: { ...look }, open: false, notes: false, instructions: '', modes: [], key: ++keys });
		chosen = draft.length - 1;
		confirming = null;
		queueMicrotask(() => nameField?.focus());
	}

	function remove(i: number): void {
		const t = draft[i];
		if (!t) return;
		if (t.modes.length && confirming !== t.key) {
			confirming = t.key;
			return;
		}
		confirming = null;
		draft.splice(i, 1);
		chosen = Math.min(i, draft.length - 1);
	}

	function modesText(modes: string[]): string {
		return modes.length > 1 ? `${modes.slice(0, -1).join(', ')} and ${modes.at(-1)}` : (modes[0] ?? '');
	}

	async function save(body: Record<string, unknown>): Promise<void> {
		if (busy) return;
		const blank = draft.findIndex((t) => !t.name.trim());
		if (!body.defaults && blank >= 0) {
			chosen = blank;
			said = 'Every type needs a name.';
			return;
		}
		busy = true;
		said = '';
		const named = taking ? draft.find((t) => t.key === taking?.key)?.name.trim() : undefined;
		const res = await write('types-save', body);
		busy = false;
		if (!res.ok) {
			said = res.error?.message ?? 'the publisher refused it';
			return;
		}
		// the new type a format menu or a popup started goes to what started it, by the id loom gave it
		const saved = (res as { types?: AnnotationType[] }).types ?? [];
		const made = named && !body.defaults ? saved.find((t) => t.name === named) : undefined;
		if (made && taking) {
			const take = taking.take;
			if (take.kind === 'hand') hand.set({ type: made.id, over: {} });
			else {
				const a = store.manifest?.annotations[take.id];
				if (a) void edit(a, { type: made.id, look: null });
			}
		}
		taking = null;
		// what was saved is the quilt's now: the draft is taken afresh when the new types arrive
		base = '';
		seen = '';
		await store.refresh();
	}

	function revert(): void {
		taking = null;
		take();
		confirming = null;
		said = '';
	}

	function rows(e: KeyboardEvent): void {
		if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
		e.preventDefault();
		chosen = Math.max(0, Math.min(draft.length - 1, chosen + (e.key === 'ArrowDown' ? 1 : -1)));
		confirming = null;
	}
</script>

<div class="types" data-testid="settings-annotations">
	<p class="sub">A type labels an annotation and sets its look. Every type is optional: an annotation can have none, and deleting a type leaves its annotations untyped, looking as they did. The types live in one file in the quilt that you and agents can both edit.</p>
	<div class="tp-grid">
		<div class="tp-list" role="tablist" aria-label="Annotation types" aria-orientation="vertical" tabindex="-1" onkeydown={rows}>
			{#each draft as t, i (t.key)}
				<button type="button" class="tp-row" class:on={i === chosen} role="tab" aria-selected={i === chosen} data-testid="type-tab" data-type={t.id ?? ''} onclick={() => ((chosen = i), (confirming = null))}>
					<span class="tn">{#if t.name.trim()}<Sample look={t.look} text={t.name} />{:else}<span class="untitled">Untitled</span>{/if}</span>
					<span class="tm">{t.open ? 'Open until resolved' : 'Only informs'}{t.notes ? ' · in Notes' : ''}</span>
				</button>
			{/each}
			{#if editable}<button type="button" class="tp-add lnk" data-testid="types-add" onclick={() => add()}>+ Add type</button>{/if}
		</div>
		{#if current}
			{@const t = current}
			<div class="tp-detail" role="tabpanel">
				<div class="tp-top">
					<input class="tp-name" placeholder="Name, for example Hint" aria-label="Type name" disabled={!editable} bind:this={nameField} bind:value={t.name} data-testid="type-name" />
					{#if editable}<button type="button" class="btn small" data-testid="type-delete" onclick={() => remove(chosen)}>Delete type</button>{/if}
				</div>
				{#if confirming === t.key}
					<div class="ce-warn" role="alert" data-testid="type-delete-warn">
						<span>The {modesText(t.modes)} mode{t.modes.length > 1 ? 's use' : ' uses'} this type. If you delete it, agents there leave untyped annotations instead.</span>
						<button type="button" class="btn small" data-testid="type-delete-yes" onclick={() => remove(chosen)}>Delete</button>
						<button type="button" class="lnk" onclick={() => (confirming = null)}>Keep it</button>
					</div>
				{/if}
				<section class="tp-sec">
					<h4>Look</h4>
					<p class="tp-sample">Marked words <Sample look={t.look} text="look like this" /> in the text.</p>
					<LookControls look={t.look} words disabled={!editable} onpick={(c) => (t.look = { ...t.look, ...c })} />
				</section>
				<section class="tp-sec">
					<h4>Resolving</h4>
					<div class="tp-radio" role="radiogroup" aria-label="Resolving">
						{#each [[true, 'Stays open until resolved', 'In To do for everyone but its writer, with a Resolve button, until someone resolves it.'], [false, 'Only informs', 'Never open: no Resolve button, and never in To do.']] as const as [v, name, hint] (name)}
							<label class="tp-opt" class:on={t.open === v}>
								<input type="radio" name="open-{t.key}" checked={t.open === v} disabled={!editable} data-testid="type-open-{v}" onchange={() => (t.open = v)} />
								<span><b>{name}</b><span class="tp-hint">{hint}</span></span>
							</label>
						{/each}
					</div>
				</section>
				<section class="tp-sec">
					<h4>Notes</h4>
					<label class="chk"><input type="checkbox" bind:checked={t.notes} disabled={!editable} data-testid="type-notes" />List in Notes</label>
					<p class="tp-hint">Annotations of this type also appear in Notes, from every document, each linked back to where it was left.</p>
				</section>
				<section class="tp-sec">
					<h4>Instructions for agents</h4>
					<p class="tp-hint">When to use this type. Agents read it with the instructions for every annotation.</p>
					<textarea class="tp-ins" aria-label="Instructions for agents" placeholder="When should an agent use this type?" disabled={!editable} bind:value={t.instructions} data-testid="type-instructions"></textarea>
					<p class="tp-used" data-testid="type-modes">{t.modes.length ? `Used by the ${modesText(t.modes)} mode${t.modes.length > 1 ? 's' : ''}.` : 'No mode names this type. Agents use it wherever these instructions fit.'}</p>
				</section>
			</div>
		{:else}
			<div class="tp-detail"><p class="tp-hint">No types. Add one, or restore the defaults.</p></div>
		{/if}
	</div>
	{#if editable}
		<div class="tp-foot">
			<button type="button" class="lnk" disabled={busy} data-testid="types-defaults" onclick={() => void save({ defaults: true })}>Restore defaults</button>
			{#if said}<span class="said" role="alert" data-testid="types-said">{said}</span>{/if}
			{#if dirty}
				<span class="what">Unsaved changes to the types</span>
				<button type="button" class="btn" disabled={busy} data-testid="types-revert" onclick={revert}>Revert</button>
				<button type="button" class="btn primary" disabled={busy} data-testid="types-save" onclick={() => void save({ types: payload(draft) })}>{busy ? 'Saving…' : 'Save'}</button>
			{/if}
		</div>
	{/if}
</div>

<style>
	.types {
		display: grid;
		gap: 12px;
		font-family: var(--sans);
		font-size: 13px;
	}
	.sub {
		margin: 0;
		color: var(--ink-soft);
		line-height: 1.45;
	}
	.tp-grid {
		display: grid;
		grid-template-columns: 210px minmax(0, 1fr);
		gap: 14px;
		min-height: 320px;
	}
	.tp-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding-right: 10px;
		border-right: 1px solid var(--rule);
		outline: none;
	}
	.tp-row {
		display: grid;
		gap: 2px;
		padding: 6px 8px;
		font: inherit;
		text-align: left;
		color: var(--ink);
		background: none;
		border: 0;
		border-radius: 6px;
		cursor: pointer;
	}
	.tp-row:hover {
		background: var(--leaf);
	}
	.tp-row.on {
		background: var(--accent-wash);
	}
	.tn {
		font-family: var(--body-face);
		font-size: 14px;
	}
	.untitled {
		color: var(--ink-faint);
		font-style: italic;
	}
	.tm {
		font-size: 11.5px;
		color: var(--ink-faint);
	}
	.tp-add {
		margin-top: 6px;
		align-self: flex-start;
		padding: 4px 8px;
	}
	.tp-detail {
		display: grid;
		align-content: start;
		gap: 14px;
		min-width: 0;
	}
	.tp-top {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.tp-name {
		flex: 1;
		min-width: 0;
		padding: 5px 8px;
		font-family: var(--body-face);
		font-size: 16px;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 6px;
	}
	.tp-sec {
		display: grid;
		gap: 6px;
	}
	.tp-sec h4 {
		margin: 0;
		font-size: 10.5px;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	.tp-sample {
		margin: 0;
		font-family: var(--body-face);
		font-size: 14px;
	}
	.tp-hint {
		display: block;
		margin: 0;
		font-size: 12px;
		line-height: 1.4;
		color: var(--ink-soft);
	}
	.tp-radio {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.tp-opt {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 8px 10px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		cursor: pointer;
	}
	.tp-opt.on {
		border-color: var(--accent);
		background: var(--accent-wash);
	}
	.tp-opt span {
		display: grid;
		gap: 2px;
	}
	.chk {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.tp-ins {
		width: 100%;
		box-sizing: border-box;
		min-height: 140px;
		padding: 8px;
		font-family: var(--body-face);
		font-size: 13.5px;
		line-height: 1.45;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 6px;
		resize: vertical;
	}
	.tp-used {
		margin: 0;
		font-size: 12px;
		color: var(--ink-soft);
	}
	.ce-warn {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 10px;
		padding: 8px 10px;
		font-size: 12.5px;
		background: color-mix(in srgb, var(--ann-orange-band) 35%, var(--sheet));
		border: 1px solid var(--ann-orange);
		border-radius: 6px;
	}
	.ce-warn span {
		flex: 1 1 220px;
	}
	.tp-foot {
		display: flex;
		align-items: center;
		gap: 10px;
		padding-top: 10px;
		border-top: 1px solid var(--rule);
	}
	.what {
		margin-left: auto;
		color: var(--ink-soft);
	}
	.said {
		color: var(--state-stale);
	}
	.lnk {
		padding: 0;
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.lnk:hover:not(:disabled) {
		text-decoration: underline;
	}
	@media (max-width: 640px) {
		.tp-grid {
			grid-template-columns: 1fr;
		}
		.tp-list {
			border-right: 0;
			padding-right: 0;
		}
		.tp-radio {
			grid-template-columns: 1fr;
		}
	}
</style>
