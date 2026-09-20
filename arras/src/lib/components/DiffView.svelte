<script lang="ts">
	import { dataUrl } from '$lib/paths';
	// A unified diff shown as two tinted columns (book 15.3.5): what was accepted on the left, what is there now on the right.
	let { path }: { path: string } = $props();

	type Row = { left: string; right: string; kind: 'same' | 'change' | 'hunk' };

	let rows = $state<Row[]>([]);
	let error = $state('');

	/** Pairs a run of removed lines with the run of added lines that follows it, so a rewritten line sits opposite its replacement. */
	function pair(text: string): Row[] {
		const out: Row[] = [];
		const lines = text.split('\n');
		let i = 0;
		while (i < lines.length) {
			const ln = lines[i];
			if (ln.startsWith('--- ') || ln.startsWith('+++ ')) {
				i++;
				continue;
			}
			if (ln.startsWith('@@')) {
				out.push({ left: ln, right: '', kind: 'hunk' });
				i++;
				continue;
			}
			if (ln.startsWith('-') || ln.startsWith('+')) {
				const removed: string[] = [];
				const added: string[] = [];
				while (i < lines.length && lines[i].startsWith('-')) removed.push(lines[i++].slice(1));
				while (i < lines.length && lines[i].startsWith('+')) added.push(lines[i++].slice(1));
				for (let j = 0; j < Math.max(removed.length, added.length); j++) {
					out.push({ left: removed[j] ?? '', right: added[j] ?? '', kind: 'change' });
				}
				continue;
			}
			out.push({ left: ln.slice(1), right: ln.slice(1), kind: 'same' });
			i++;
		}
		while (out.length && out[out.length - 1].kind === 'same' && !out[out.length - 1].left.trim()) out.pop();
		return out;
	}

	$effect(() => {
		const url = dataUrl(path);
		void fetch(url)
			.then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status}`))))
			.then((t) => {
				rows = pair(t);
				error = '';
			})
			.catch((e: Error) => {
				error = e.message;
				rows = [];
			});
	});
</script>

{#if error}
	<p class="faint">the diff is unavailable ({error})</p>
{:else}
	<table class="diff" data-testid="diff">
		<tbody>
			{#each rows as r, i (i)}
				<tr class={r.kind}>
					{#if r.kind === 'hunk'}
						<td class="hunk" colspan="2">{r.left}</td>
					{:else}
						<td class="l">{r.left}</td>
						<td class="r">{r.right}</td>
					{/if}
				</tr>
			{/each}
		</tbody>
	</table>
{/if}

<style>
	table.diff {
		border-collapse: collapse;
		width: 100%;
		font-family: var(--mono);
		font-size: 10px;
		line-height: 1.5;
		table-layout: fixed;
	}
	td {
		padding: 0 6px;
		vertical-align: top;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		width: 50%;
	}
	tr.change .l {
		background: var(--state-incomplete-wash);
		color: var(--state-incomplete);
	}
	tr.change .r {
		background: var(--state-accepted-wash);
		color: var(--state-accepted);
	}
	td.hunk {
		color: var(--ink-faint);
		background: var(--leaf);
	}
</style>
