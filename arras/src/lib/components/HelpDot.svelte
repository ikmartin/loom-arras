<script lang="ts">
	// The question-mark circle beside a page title (book 15.3.5): what the page means, what each state means, and which command records it.
	import Popover from '$lib/components/Popover.svelte';

	let { label, topic }: { label: string; topic: 'review' | 'problems' | (string & {}) } = $props();

	const TOPICS: Record<string, { title: string; body: string; states?: [string, string][]; command: string }> = {
		review: {
			title: 'What the review panel shows',
			body: 'One row per statement and per proof. The state is what was last recorded for that exact text. When a text that was accepted has since changed, the row says so and can show the change; when a text marks a gap in itself, the row says what rests on it. Acceptance is recorded from the command line; this page only reads it back.',
			states: [
				['accepted', 'someone recorded that this text, as it stands, is correct'],
				['stale', 'the text was accepted and has changed since, or something it depends on has'],
				['draft', 'nothing has been recorded about this text'],
				['incomplete', 'the text marks a gap in itself, so it is not a finished argument'],
				['not in a document', 'no document includes this node, so nothing depends on it yet']
			],
			command: 'accept'
		},
		problems: {
			title: 'What the problems page shows',
			body: 'Every diagnostic the publisher raised, by severity and code. An error means the published corpus is wrong in a way a reader would notice; a warning means something is probably a mistake; information is a remark.',
			command: 'lint'
		}
	};

	const t = $derived(TOPICS[topic] ?? { title: label, body: '', command: '' });
</script>

<Popover placement="below" width={320} role="note" testid="help-panel-{topic}">
	{#snippet trigger({ open, toggle })}
		<button aria-label={label} aria-expanded={open} title={label} onclick={toggle} data-testid="help-{topic}">?</button>
	{/snippet}
	<div class="pop">
		<p class="title">{t.title}</p>
		<p>{t.body}</p>
		{#if t.states}
			<dl>
				{#each t.states as [name, meaning] (name)}
					<dt>{name}</dt>
					<dd>{meaning}</dd>
				{/each}
			</dl>
		{/if}
		{#if t.command}<p class="cmd">Recorded and reported by the command line: <code>{t.command}</code>. Run it with <code>--help</code> for what it takes.</p>{/if}
	</div>
</Popover>

<style>
	button {
		width: 15px;
		height: 15px;
		border-radius: 999px;
		border: 1px solid var(--rule-strong);
		background: var(--leaf);
		color: var(--ink-faint);
		font-family: var(--sans);
		font-size: 9px;
		line-height: 1;
		cursor: pointer;
		vertical-align: middle;
	}
	button:hover {
		color: var(--link);
		border-color: var(--link);
	}
	.pop {
		padding: var(--gap);
		font-family: var(--sans);
		font-size: 11px;
		line-height: 1.55;
		color: var(--ink-soft);
		text-transform: none;
		letter-spacing: 0;
	}
	.pop p {
		margin: 0 0 var(--gap-tight);
	}
	.pop .title {
		color: var(--ink);
		font-weight: 500;
	}
	dl {
		margin: 0 0 var(--gap-tight);
		display: grid;
		grid-template-columns: 74px 1fr;
		gap: 2px var(--gap-tight);
	}
	dt {
		color: var(--ink);
	}
	dd {
		margin: 0;
	}
	.cmd {
		color: var(--ink-faint);
		margin-bottom: 0;
	}
</style>
