<script lang="ts">
	// The input at the foot of the Chat (plan 0.14): what a person types to the agent working in the same session.
	//
	// **Loom is a mailbox.** This posts; loom appends; a parked agent wakes because a file grew. What happened to the message — who was listening, or that it waits — is the Chat's status line to say, from the answer this hands back (`onsent`), so it is said in one place.
	import { can, write } from '$lib/write';
	import type { Posted } from './transcript.svelte';

	let { session, packed = 0, onsent }: { session: string; packed?: number; onsent?: (res: Posted) => void } = $props();

	let allowed = $state(false);
	let text = $state('');
	let busy = $state(false);
	let refused = $state('');
	/** Two lines, or eight for a message worth writing at length. */
	let wide = $state(false);

	$effect(() => {
		void can('message').then((ok) => (allowed = ok));
	});

	async function send(): Promise<void> {
		const body = text.trim();
		// words, or what was marked, or both; a packet goes on its own when there are no words
		if ((!body && !packed) || busy) return;
		busy = true;
		refused = '';
		const res: Posted = await write('message', { text: body, session });
		busy = false;
		if (!res.ok) {
			refused = res.error?.message ?? 'the publisher refused it';
			return;
		}
		text = '';
		onsent?.(res);
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
	<form class="composer" data-testid="composer" onsubmit={(e) => (e.preventDefault(), send())}>
		<textarea
			rows={wide ? 8 : 2}
			placeholder={packed ? 'say something, or send what you marked…' : 'say something…'}
			aria-label="Post a message to this session"
			bind:value={text}
			onkeydown={keys}
			data-testid="composer-text"
		></textarea>
		<button type="button" class="grow" title={wide ? 'Fewer lines' : 'More lines'} aria-expanded={wide} data-testid="composer-expand" onclick={() => (wide = !wide)}>{wide ? '⌄' : '⌃'}</button>
		<button type="submit" disabled={busy || (!text.trim() && !packed)} data-testid="composer-send">send</button>
		{#if refused}<p class="refused" role="alert" data-testid="composer-refused">{refused}</p>{/if}
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
	.grow {
		padding: 2px 6px;
	}
	.refused {
		grid-column: 1 / -1;
		margin: 0;
		font-size: 0.76rem;
		color: var(--annotation, #c05621);
	}
</style>
