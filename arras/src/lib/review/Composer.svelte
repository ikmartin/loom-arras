<script lang="ts">
	// Writing an annotation from the text it is about (plan 0.11 Part H, specs/write-api.md §5).
	//
	// The quote is the reader's selection, which is what anchors the finding to a sentence rather than to a node. A selection that crosses converted markup cannot always be recovered exactly, so the publisher is allowed to refuse, and its refusal is shown rather than swallowed: a comment that silently landed on the wrong sentence is worse than one that did not land.
	import { can, write } from '$lib/write';
	import { GRADED, KINDS, SEVERITIES } from '$lib/review/kinds';

	let {
		target,
		onwritten = undefined
	}: {
		/** The key or document path the annotation is about. */
		target: string;
		onwritten?: () => void;
	} = $props();

	let allowed = $state(false);
	let open = $state(false);
	let quote = $state('');
	let message = $state('');
	let kind = $state('question');
	let severity = $state('');
	let busy = $state(false);
	let said = $state('');

	$effect(() => {
		can('comment').then((ok) => (allowed = ok));
	});

	function takeSelection() {
		const text = (window.getSelection()?.toString() ?? '').trim();
		if (text) quote = text;
		open = true;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!message.trim() || busy) return;
		busy = true;
		said = '';
		const res = await write('comment', {
			target,
			message: message.trim(),
			quote: quote.trim() || undefined,
			kind,
			severity: (GRADED.includes(kind) && severity) || undefined
		});
		busy = false;
		if (res.ok) {
			said = 'written';
			message = '';
			quote = '';
			open = false;
			onwritten?.();
		} else {
			// The publisher's own words: "quote not found" means something different from "no such key", and a reader
			// who is told only "failed" has to guess which.
			said = res.error?.message ?? 'the publisher refused it';
		}
	}
</script>

{#if allowed}
	<div class="composer" data-testid="composer">
		{#if !open}
			<button class="open" onclick={takeSelection} data-testid="composer-open">
				Comment{#if (window.getSelection()?.toString() ?? '').trim()} on the selection{/if}
			</button>
		{:else}
			<form onsubmit={submit}>
				<label class="field">
					<span>on</span>
					<!-- Editable, because a selection that crossed a formula picks up more than the reader meant and the fix is to trim it, not to start again. -->
					<input bind:value={quote} placeholder="the exact text this is about (optional)" data-testid="composer-quote" />
				</label>
				<label class="field">
					<span>says</span>
					<textarea bind:value={message} rows="3" required placeholder="what you want to say" data-testid="composer-message"></textarea>
				</label>
				<div class="row">
					<label>kind
						<select bind:value={kind} data-testid="composer-kind">
							{#each KINDS as k (k)}<option value={k}>{k}</option>{/each}
						</select>
					</label>
					{#if GRADED.includes(kind)}
						<label>severity
							<select bind:value={severity} data-testid="composer-severity">
								{#each SEVERITIES as s (s)}<option value={s}>{s || 'none'}</option>{/each}
							</select>
						</label>
					{/if}
					<button type="submit" disabled={busy || !message.trim()} data-testid="composer-submit">{busy ? 'writing…' : 'write'}</button>
					<button type="button" onclick={() => (open = false)}>cancel</button>
				</div>
			</form>
		{/if}
		{#if said}<p class="said" role="status" data-testid="composer-said">{said}</p>{/if}
	</div>
{/if}

<style>
	.composer {
		margin: var(--gap) 0;
		font-family: var(--sans);
		font-size: 0.85em;
	}
	button {
		background: none;
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 0.2em 0.6em;
		font: inherit;
		color: var(--ink-soft);
		cursor: pointer;
	}
	button[type='submit'] {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
	button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.field {
		display: grid;
		grid-template-columns: 4em minmax(0, 1fr);
		gap: var(--gap-tight);
		align-items: baseline;
		margin-bottom: var(--gap-tight);
	}
	.field > span {
		color: var(--ink-faint);
	}
	input,
	textarea {
		font: inherit;
		font-family: var(--body-face, inherit);
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 0.3em 0.4em;
		background: var(--sheet);
		color: var(--ink);
		width: 100%;
	}
	.row {
		display: flex;
		gap: var(--gap);
		align-items: baseline;
		flex-wrap: wrap;
	}
	.said {
		color: var(--ink-faint);
		margin: var(--gap-tight) 0 0;
	}
</style>
