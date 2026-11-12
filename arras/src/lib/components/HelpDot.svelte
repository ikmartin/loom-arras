<script lang="ts">
	// The question-mark circle beside a page title: what the page means, what each state means, and, where one records it, which command.
	import Popover from '$lib/components/Popover.svelte';

	let { label, topic }: { label: string; topic: 'review' | 'problems' | (string & {}) } = $props();

	const TOPICS: Record<string, { title: string; body: string; states?: [string, string][]; command: string }> = {
		review: {
			title: 'What the Your Changes page shows',
			body: "The mathematics first: every statement and proof you have not accepted as it stands, one document at a time, each listed once with every reason it waits. Accepting records your reading of the text against what it rests on; it goes stale when either changes. Blocks taken in from an agent's copy or a pull are grouped by where they came from; what loom cannot accept says why in its row. Then the changes waiting to be kept, by document: suggestions not yet kept or discarded and, where the quilt reviews edits made in place (Settings › Agents), edits made in your files since your look, each a few words out and a few words in. Keep writes a suggestion into its file, or takes an edit into your look; Discard drops a suggestion, or writes your words back over an edit, its text kept as a version first. Neither says whether the mathematics is right, and each acts as it does in the document. To do adds the open annotations from others.",
			states: [
				['changed since you accepted', 'the text, or something it rests on, changed after you accepted it'],
				['taken in', "it came in from an agent's copy or a pull, and you have not accepted it since"],
				['never accepted', 'nothing has been recorded about this text; these are listed and not counted'],
				["can't be accepted yet", 'it is marked incomplete, it is a conjecture or question, its basis is not said, or something it rests on cannot be identified; the row says which'],
				['suggestion', 'words someone proposes in place of yours, not yet in the file'],
				['edit in the file', 'words that differ from what you last saw, whoever changed them, where the quilt reviews edits made in place']
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
