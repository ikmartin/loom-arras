<script lang="ts">
	// The composer: what a person types to an agent working in the same session (plan 0.13 §8).
	//
	// **Loom is a mailbox.** This posts; loom appends; nothing is launched. A parked agent wakes because a file grew,
	// and an agent mid-compile sees the message when it finishes and asks again. Loom holds no credentials and calls no
	// model — the agent is already running in the author's own terminal (DR-195).
	//
	// **A message lands whether or not anybody is listening**, and this says which. Refusing would lose what was typed,
	// for a reason the browser cannot fix; saying nothing would let the author believe it was delivered.
	import { can, write, type WriteResult } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import { active } from './sessions.svelte';

	let { session = '' }: { session?: string } = $props();

	interface Posted {
		session?: string;
		attached?: { who: string; kind: string }[];
	}

	const here = $derived(active(store.manifest));
	const into = $derived(session || here?.id || '');
	let allowed = $state(false);
	let text = $state('');
	let busy = $state(false);
	let said = $state('');
	let listening = $state<{ who: string; kind: string }[] | null>(null);
	/** Docked at two lines; a message worth writing at length gets the pane's full width rather than a scrollbar. */
	let wide = $state(false);

	$effect(() => {
		void can('message').then((ok) => (allowed = ok));
	});

	async function send(): Promise<void> {
		const body = text.trim();
		if (!body || busy) return;
		busy = true;
		said = '';
		const res: WriteResult & Posted = await write('message', into ? { text: body, session: into } : { text: body });
		busy = false;
		if (!res.ok) {
			said = res.error?.message ?? 'the publisher refused it';
			return;
		}
		text = '';
		listening = res.attached ?? [];
		said = listening.length
			? 'sent to ' + listening.map((a) => `${a.who} (${a.kind})`).join(', ')
			: `nobody is attached — it waits in the inbox. Start one with: loom session watch ${res.session ?? into}`;
	}

	function keys(e: KeyboardEvent): void {
		// Enter sends, because this is a message and not a document; a newline needs the modifier that says so
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			void send();
		}
	}
</script>

{#if allowed}
	<form class="composer" class:wide data-testid="composer" onsubmit={(e) => (e.preventDefault(), send())}>
		<textarea
			rows={wide ? 8 : 2}
			placeholder="say something…"
			aria-label="Post a message to this session"
			bind:value={text}
			onkeydown={keys}
			data-testid="composer-text"
		></textarea>
		<button
			type="button"
			class="grow"
			title={wide ? 'Dock it again' : 'Give it the full pane'}
			aria-expanded={wide}
			data-testid="composer-expand"
			onclick={() => (wide = !wide)}>{wide ? '⌄' : '⌃'}</button
		>
		<button type="submit" disabled={busy || !text.trim()} data-testid="composer-send">send</button>
		{#if said}
			<p class="said" role="status" data-testid="composer-said">{said}</p>
		{/if}
	</form>
{/if}

<style>
	.composer {
		display: grid;
		grid-template-columns: 1fr auto auto;
		gap: 4px;
		align-items: end;
		padding: 6px;
		border-top: 1px solid var(--rule, #ddd9cf);
	}
	textarea {
		font: inherit;
		font-size: 0.85rem;
		resize: vertical;
		min-height: 2.4em;
	}
	button {
		font: inherit;
		font-size: 0.8rem;
		color: inherit;
		background: none;
		border: 1px solid var(--rule, #ddd9cf);
		border-radius: 3px;
		padding: 2px 10px;
		cursor: pointer;
	}
	button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.composer.wide {
		position: absolute;
		inset: auto 0 0 0;
		background: var(--sheet, #fff);
		box-shadow: 0 -2px 12px rgb(0 0 0 / 10%);
		z-index: 20;
	}
	.grow {
		padding: 2px 6px;
	}
	.said {
		grid-column: 1 / -1;
		margin: 0;
		font-size: 0.76rem;
		color: var(--ink-faint, #6b6b6b);
	}
</style>
