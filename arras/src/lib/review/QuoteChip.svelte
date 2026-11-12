<script lang="ts">
	// Quote, on a bare selection: copies the words and where they came from, as a link an agent can follow, and says so. It writes nothing; a quote is not a record.
	import Icon from '$lib/components/Icon.svelte';
	import { copyText } from '$lib/clipboard';
	import AtSelection from './AtSelection.svelte';
	import { quoted } from './annotating.svelte';
	import { say } from './toasts.svelte';

	type Box = { left: number; top: number; width: number; height: number };

	let {
		at,
		range,
		words,
		name,
		href,
		ondone
	}: {
		at: Box;
		range?: Range;
		/** The words selected, as the clipboard takes them. */
		words: string;
		/** Where they are, as a reader names it. */
		name: string;
		/** A link to the place: `quilt:` or `cited:`. */
		href: string;
		/** The chip has done its work and goes. */
		ondone: () => void;
	} = $props();

	async function quote(): Promise<void> {
		const said = { words, name };
		const ok = await copyText(quoted(words, name, href));
		window.getSelection()?.removeAllRanges();
		ondone();
		say({ title: 'Quoted for your agent', words: said.words, lines: [`— ${said.name}`, ok ? 'Copied with where it came from. Paste it to your agent.' : 'This browser refused the clipboard, so nothing was copied.'] });
	}
</script>

<AtSelection {at} {range}>
	<button type="button" class="chip" title="Quote these words to your agent, with where they came from" data-testid="quote-offer" onclick={() => void quote()}><Icon name="quote" size={14} />Quote</button>
</AtSelection>
