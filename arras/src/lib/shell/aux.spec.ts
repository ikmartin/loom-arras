import { describe, expect, it } from 'vitest';
import { coerce } from '$lib/prefs.svelte';
import { isAgentConfig, isAux } from './aux';

describe("LaTeX's auxiliary files", () => {
	it('are what a compile writes for its own next run, never a source or its output', () => {
		for (const p of ['paper/main.aux', 'main.log', 'paper/main.synctex.gz', 'main.fdb_latexmk', 'main.fls', 'main.bbl', 'main.blg', 'main.bcf', 'main.run.xml', 'main.toc', 'talk.nav', 'talk.snm', 'main-blx.bib', 'main.synctex(busy)'])
			expect(isAux(p), p).toBe(true);
		for (const p of ['paper/main.tex', 'paper/main.pdf', 'refs.bib', 'macros.sty', 'notes/a.md', 'logs/run.txt', 'catalog.json'])
			expect(isAux(p), p).toBe(false);
	});

	it('are hidden unless the reader says otherwise, and a stored choice is kept', () => {
		expect(coerce({}).hideAux).toBe(true);
		expect(coerce({ hideAux: false }).hideAux).toBe(false);
	});
});

describe("the agents' config documents", () => {
	it('are known by name wherever they stand, and nothing else is', () => {
		for (const p of ['AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'notes/CLAUDE.md', 'CLAUDE.local.md', 'AGENT.md']) expect(isAgentConfig(p), p).toBe(true);
		for (const p of ['README.md', 'agents.md', 'notes/AGENTS.md.bak', 'MY-CLAUDE.md', 'drafting/main.tex']) expect(isAgentConfig(p), p).toBe(false);
	});
});
