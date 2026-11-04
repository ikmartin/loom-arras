<script lang="ts">
	// The question-mark circle beside a page title: what the page means, what each state means, and, where one records it, which command.
	import Popover from '$lib/components/Popover.svelte';

	let { label, topic }: { label: string; topic: 'review' | 'problems' | (string & {}) } = $props();

	const TOPICS: Record<string, { title: string; body: string; states?: [string, string][]; command: string }> = {
		review: {
			title: 'What your text shows',
			body: "What changed in your documents and files since your look, and every statement and proof you have not accepted as it stands. A block is listed once, with every reason it waits. Keep takes an edit into your look, and Undo puts it back, keeping the text it replaces; neither says whether the mathematics is right. Accepting records your reading of the text against what it rests on, and keeps its edit too; it goes stale when either changes. Blocks taken in from an agent's copy or a pull are grouped by where they came from. A block's name opens it in its document with why it waits beside it; what loom cannot accept says why in its row.",
			states: [
				['edited since your look', 'its text differs from what you last saw, whoever changed it'],
				['changed since you accepted', 'the text, or something it rests on, changed after you accepted it'],
				['taken in', "it came in from an agent's copy or a pull, and you have not accepted it since"],
				['never accepted', 'nothing has been recorded about this text; these are listed and not counted'],
				["can't be accepted yet", 'it is marked incomplete, it is a conjecture or question, its basis is not said, or something it rests on cannot be identified; the row says which']
			],
			command: ''
		},
		problems: {
			title: 'What the problems page shows',
			body: "What the publisher found wrong, by whose it is to put right. Your files come first, and are what Review counts; an agent's copy is the agent's, or yours to leave out when you take it back; a cited work's digest is loom's reading of the paper, mended by digesting the work again.",
			states: [
				['error', 'a reader would notice it: a reference to nothing, an id defined twice'],
				['warning', 'probably a mistake, though the document still reads'],
				['remark', 'worth knowing, and not wrong']
			],
			command: ''
		}
	};

	const t = $derived(TOPICS[topic] ?? { title: label, body: '', command: '' });
</script>

<Popover placement="below" width={320} role="note" testid="help-panel-{topic}">
	{#snippet trigger({ open, toggle })}
		<button class="help" aria-label={label} aria-expanded={open} title={label} onclick={toggle} data-testid="help-{topic}">?</button>
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
