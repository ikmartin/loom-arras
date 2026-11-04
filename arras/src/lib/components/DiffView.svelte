<script lang="ts">
	import type { Snippet } from 'svelte';
	import { dataUrl } from '$lib/paths';
	// A unified diff shown as two tinted columns: what was accepted on the left, what is there now on the right. `hunk`, when given, draws the controls for one change in its `@@` row, numbered from 0 as the publisher numbers them; `only` draws just those changes, by the same numbers, so a block shows its own edit out of its file's. A diff keeps its path as it changes, so `version` says when to read it again.
	let { path, hunk, only, version }: { path: string; hunk?: Snippet<[number]>; only?: number[]; version?: string } = $props();

	type Row = { left: string; right: string; kind: 'same' | 'change' | 'hunk'; n?: number; of: number };

	let all = $state<Row[]>([]);
	const rows = $derived(only ? all.filter((r) => only.includes(r.of)) : all);
	let error = $state('');

	/** Pairs a run of removed lines with the run of added lines that follows it, so a rewritten line sits opposite its replacement. */
	function pair(text: string): Row[] {
		const out: Row[] = [];
		const lines = text.split('\n');
		let i = 0;
		let n = 0;
		while (i < lines.length) {
			const ln = lines[i];
			if (ln.startsWith('--- ') || ln.startsWith('+++ ')) {
				i++;
				continue;
			}
			if (ln.startsWith('@@')) {
				out.push({ left: ln, right: '', kind: 'hunk', n: n, of: n });
				n++;
				i++;
				continue;
			}
			if (ln.startsWith('-') || ln.startsWith('+')) {
				const removed: string[] = [];
				const added: string[] = [];
				while (i < lines.length && lines[i].startsWith('-')) removed.push(lines[i++].slice(1));
				while (i < lines.length && lines[i].startsWith('+')) added.push(lines[i++].slice(1));
				for (let j = 0; j < Math.max(removed.length, added.length); j++) {
					out.push({ left: removed[j] ?? '', right: added[j] ?? '', kind: 'change', of: n - 1 });
				}
				continue;
			}
			out.push({ left: ln.slice(1), right: ln.slice(1), kind: 'same', of: n - 1 });
			i++;
		}
		while (out.length && out[out.length - 1].kind === 'same' && !out[out.length - 1].left.trim()) out.pop();
		return out;
	}

	$effect(() => {
		void version;
		const url = dataUrl(path);
		void fetch(url)
			.then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status}`))))
			.then((t) => {
				all = pair(t);
				error = '';
			})
			.catch((e: Error) => {
				error = e.message;
				all = [];
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
						<td class="hunk" colspan="2"><span>{r.left}</span>{#if hunk && r.n !== undefined}<span class="hunk-acts" data-testid="hunk-acts" data-hunk={r.n}>{@render hunk(r.n)}</span>{/if}</td>
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
	/* a change's controls stand at the end of its `@@` row, in the viewer's own face rather than the diff's */
	td.hunk:has(.hunk-acts) {
		padding: 3px 6px;
	}
	.hunk-acts {
		float: right;
		display: inline-flex;
		align-items: center;
		gap: var(--gap-tight);
		font-family: var(--sans);
		font-size: 12px;
		color: var(--ink-soft);
		white-space: normal;
	}
</style>
