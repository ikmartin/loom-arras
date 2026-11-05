// What the ledger says about each cited work (plan 0.13.3, View 4): one fact per column, each a question a reader asks of the Library — can I read it here, how much has been read off it, does my text lean on it, what has a person vouched for, what awaits my judgment, what is unanswered on it. Model facts in, display facts out, like `reached.ts`; nothing here renders.

import { isAgentDocument } from '$lib/manifest/documents';
import type { Manifest, Reference } from '$lib/manifest/types';
import { reachedExternal } from '$lib/reached';
import { bibText, surnames } from '$lib/works';

export interface LedgerRow {
	citekey: string;
	title: string;
	/** A copy of the paper is filed here, so opening the work gives its pages. */
	filed: boolean;
	/** Why nothing can be read off it, when someone declared so; '' otherwise. */
	unreadable: string;
	/** Results read off it into its digest; 0 when it has none. */
	digest: number;
	/** Of those, the ones the corpus's own text leans on. */
	used: number;
	/** Results read off it by loom's extraction, which nobody has vouched for. */
	extracted: number;
	/** Results a person compared with the paper and vouched for. */
	verified: number;
	/** Statements an agent read off its pages that await the author's judgment. */
	proposed: number;
	/** Notes on its pages and findings on its results still awaiting an answer. */
	open: number;
	/** The work's other documents, each a citekey of its own, whose counts are folded into this row. */
	versions: string[];
	/** Its authors' surnames, as a byline gives them. */
	authors: string;
	/** The person added it by hand, rather than a document citing it. */
	added: boolean;
	/** The citekeys of this work, a version's among them, that the person's documents cite. */
	citing: string[];
	/** Where its digest's results were read from: its LaTeX `source`, its `pages`, `both`, or '' when nobody says. */
	from: 'source' | 'pages' | 'both' | '';
	/** An agent or the person wrote its overview. */
	overview: boolean;
	/** The person's keys and documents that cite it (`citedIn`). */
	cited: number;
	/** Its entry names a global identifier, so a run can look it up and fetch it. */
	identified: boolean;
	/** Lowercased key, title and authors, which the ledger's search matches. */
	text: string;
}

/**
 * The ledger's row for one work.
 *
 * Parameters
 * ----------
 * m : Manifest
 * ref : Reference
 * reached : Set<string>
 *     The external nodes the corpus leans on (`reachedExternal`), computed once for every row.
 *
 * Returns
 * -------
 * LedgerRow
 */
export function ledgerRow(m: Manifest, ref: Reference, reached: Set<string>): LedgerRow {
	const digest = ref.digest?.nodes ?? [];
	const mine = new Set(digest);
	const onResults = Object.values(m.annotations).filter(
		(a) => !a.discarded && !a.in_reply_to && a.status === 'open' && mine.has(m.keys[a.target.key]?.node ?? a.target.key)
	).length;
	const places = citedIn(m, ref).reduce((n, c) => n + Math.max(1, c.keys.length), 0);
	return {
		citekey: ref.citekey,
		title: bibText(ref.bib.title as string) || ref.citekey,
		filed: !!ref.artifacts?.pdf,
		unreadable: ref.unreadable?.why ?? '',
		digest: digest.length,
		used: digest.filter((id) => reached.has(id)).length,
		...resultCounts(ref),
		open: (ref.reading?.open ?? 0) + onResults,
		versions: [],
		authors: surnames(ref.bib.author),
		added: !!ref.added,
		citing: places ? [ref.citekey] : [],
		from: ({ extract: 'source', pdf: 'pages', mixed: 'both' } as const)[ref.digest?.method as 'extract' | 'pdf' | 'mixed'] ?? '',
		overview: !!ref.overview,
		cited: places,
		identified: !!ref.work && !ref.work.startsWith('work:'),
		text: `${ref.citekey} ${bibText(ref.bib.title as string)} ${bibText(ref.bib.author ?? '')}`.toLowerCase()
	};
}

/**
 * The ledger: one row per work, a version's counts folded into its work's row, which names it.
 *
 * Parameters
 * ----------
 * m : Manifest
 * reached : Set<string>
 *     As for `ledgerRow`.
 *
 * Returns
 * -------
 * LedgerRow[]
 *     In the manifest's order; a version whose work is not in the manifest keeps a row of its own.
 */
export function ledgerRows(m: Manifest, reached: Set<string>): LedgerRow[] {
	const rows = new Map(Object.values(m.references).map((ref) => [ref.citekey, ledgerRow(m, ref, reached)]));
	for (const ref of Object.values(m.references)) {
		const top = ref.version_of ? rows.get(ref.version_of) : undefined;
		const own = rows.get(ref.citekey);
		if (!top || !own) continue;
		top.filed ||= own.filed;
		top.overview ||= own.overview;
		top.identified ||= own.identified;
		for (const k of ['digest', 'used', 'extracted', 'verified', 'proposed', 'open', 'cited'] as const) top[k] += own[k];
		top.text += ' ' + own.text;
		top.citing.push(...own.citing);
		top.versions.push(ref.citekey);
		rows.delete(ref.citekey);
	}
	return [...rows.values()];
}

/** What deleting a work takes with it, in the words of the question asked first. */
export function goesWith(work: { pdf: boolean; results: number; verified: number; overview: boolean }): string {
	const { pdf, results, verified, overview } = work;
	const parts = [
		pdf ? "loom's copy of its PDF and its page text" : '',
		results ? `${results} result${results === 1 ? '' : 's'}${verified ? `, ${verified} of them verified by you,` : ''}` : '',
		overview ? 'its overview' : ''
	].filter(Boolean);
	const list = parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}` : parts[0];
	return (list ? `This also deletes ${list}. ` : '') + 'This cannot be undone.';
}

/** A work as the column and the palette list it: one row, whichever of its documents is filed. */
export interface ShelfRow {
	citekey: string;
	title: string;
	/** A copy of one of its documents is filed here. */
	filed: boolean;
	/** The citekey a choice opens: the work's own where its copy is filed, else a version's that is. */
	opens: string;
	unreadable: boolean;
	/** What a filter matches, lowercased: every document's key, title and authors. */
	text: string;
}

/**
 * The works a reader opens, one row each by title: a version is folded into its work, as the ledger folds it.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * ShelfRow[]
 *     Sorted by title; a version whose work is not in the manifest keeps a row of its own.
 */
export function shelf(m: Manifest): ShelfRow[] {
	const refs = Object.values(m.references ?? {});
	return refs
		.filter((r) => !r.version_of || !m.references[r.version_of])
		.map((r) => {
			const all = [r, ...refs.filter((v) => v.version_of === r.citekey)];
			const copy = all.find((x) => x.artifacts?.pdf);
			return {
				citekey: r.citekey,
				title: bibText(r.bib.title) || r.citekey,
				filed: !!copy,
				opens: (copy ?? r).citekey,
				unreadable: !!r.unreadable,
				text: all.map((x) => `${x.citekey} ${bibText(x.bib.title)} ${bibText(x.bib.author ?? '')}`).join(' ').toLowerCase()
			};
		})
		.sort((a, b) => a.title.localeCompare(b.title));
}

/** How many of a work's results are in each state a reader is told: extracted by loom, verified by a person, proposed by an agent. */
export function resultCounts(ref: Reference): { extracted: number; verified: number; proposed: number } {
	const states = Object.values(ref.results ?? {}).map((r) => r.state);
	const count = (s: string) => states.filter((x) => x === s).length;
	return { extracted: count('extracted'), verified: count('verified'), proposed: count('proposed') };
}

/**
 * Where a work's extracted results were read from, when that is another version than the bibliography cites; null otherwise.
 *
 * Parameters
 * ----------
 * ref : Reference
 *
 * Returns
 * -------
 * string | null
 *     The sentence the work's Info says, naming the artifact and what the bibliography cites.
 */
export function readFrom(ref: Reference): string | null {
	const v = Object.values(ref.results ?? {}).find((r) => r.version)?.version;
	if (!v) return null;
	if (!v.extracted_from) return 'The digest does not say what it was read from.';
	const cited = v.cited.startsWith('work:') ? 'a version it does not identify' : 'the published version';
	return `Read from ${v.extracted_from}; the bibliography cites ${cited}.`;
}

/** Whether a work wants something of the author: a statement to judge, or a question to answer. */
export function needsWork(r: LedgerRow): boolean {
	return r.proposed > 0 || r.open > 0;
}

/** What can be done about a problem, in the ledger's own terms: run on the work, run it again from scratch, upload its PDF, or stop asking for its paper. */
export type FixAct = 'run' | 'redo' | 'upload' | 'ignore';

/** A problem a work has, said in the viewer's words, with what can be done about it. */
export interface Problem {
	code: 'no-copy' | 'unidentified' | 'another-version' | 'lookup-failed' | 'not-this-work' | 'extract-failed' | 'map-failed';
	text: string;
	fixes: FixAct[];
}

/** One work's line of a run's report: what failed for it, where something did. */
export interface RunRow {
	citekey: string;
	lookup_error?: string;
	discarded?: string;
	extract_error?: string;
	map_error?: string;
	/** Its PDF holds almost no text: a scan, which opens but cannot be searched or quoted. */
	no_text?: boolean;
}

/**
 * A work's problems, each with its fixes: from the manifest, what stands on disk (its diagnostics `no-readable-copy` and `unresolved-work`, and `version_mismatch`); from the last run on it, what that run could not do, a failed lookup or fetch only for a work that does not hold its paper.
 *
 * Parameters
 * ----------
 * m : Manifest
 * ref : Reference
 * run : RunRow, optional
 *     The work's line in the report of the last run that acted on it, while the publisher still holds it.
 *
 * Returns
 * -------
 * Problem[]
 *     A work loom cannot identify is not also told it has no copy, since the one says why the other, and is told nothing once a copy is filed; a work declared unreadable has neither.
 */
export function problemsOf(m: Manifest, ref: Reference, run?: RunRow): Problem[] {
	// a code by its name after the publisher's prefix, as NodeItem reads `:missing-proof`: the publisher is never named here
	const on = (name: string) => (m.diagnostics ?? []).some((d) => d.code.endsWith(`:${name}`) && d.keys.includes(ref.citekey));
	const out: Problem[] = [];
	// an entry with no identifier matters only while a copy is wanted: one filed by hand is read all the same, and one declared unreadable is wanted no longer
	const wanted = !ref.artifacts?.pdf && !ref.artifacts?.source && !ref.unreadable;
	if (on('unresolved-work') && wanted) out.push({ code: 'unidentified', text: 'Its entry names no DOI or arXiv id, so loom cannot fetch it.', fixes: ['upload', 'ignore'] });
	else if (on('no-readable-copy') && wanted) {
		const identified = !!ref.work && !ref.work.startsWith('work:');
		out.push({ code: 'no-copy', text: 'No copy of the paper can be read here.', fixes: identified ? ['run', 'upload', 'ignore'] : ['upload', 'ignore'] });
	}
	if (ref.version_mismatch) out.push({ code: 'another-version', text: 'Its digest was read from another version than the one cited.', fixes: ['redo'] });
	// a lookup or a fetch only ever adds to what is held: holding the paper, a work has nothing to fix when one comes back empty
	if (run?.lookup_error && !ref.artifacts?.pdf) out.push({ code: 'lookup-failed', text: `The last lookup could not be made: ${run.lookup_error}`, fixes: ['run'] });
	if (run?.discarded && !ref.artifacts?.pdf) out.push({ code: 'not-this-work', text: `The paper the last run fetched was not this work: ${run.discarded}`, fixes: ['upload'] });
	if (run?.extract_error) out.push({ code: 'extract-failed', text: `Reading its results off the source failed: ${run.extract_error}`, fixes: ['redo'] });
	if (run?.map_error) out.push({ code: 'map-failed', text: `Mapping its pages failed: ${run.map_error}`, fixes: ['redo'] });
	return out;
}

/** How many works want something of the author beyond results to check, which Proposed Changes counts, as Review › Library counts them under "needs you", from what stands on disk: the last run's problems are the page's alone, since only the page follows the publisher's runs. */
export function needsYou(m: Manifest): number {
	return ledgerRows(m, reachedExternal(m)).filter((r) => {
		const ref = m.references?.[r.citekey];
		return keepRow(r, ref ? problemsOf(m, ref) : [], 'needs-you');
	}).length;
}

/** Which works the ledger shows: all, those wanting something of the person beyond results to check, those with no paper, no overview, or not cited, and those with results proposed or verified. */
export type LedgerFilter = 'all' | 'needs-you' | 'no-paper' | 'no-overview' | 'not-cited' | 'proposed' | 'verified';

/** Whether the ledger's filter `f` keeps `r`, whose problems are `problems`; a work declared unreadable has no paper to want. */
export function keepRow(r: LedgerRow, problems: Problem[], f: LedgerFilter): boolean {
	if (f === 'needs-you') return r.open > 0 || problems.length > 0;
	if (f === 'no-paper') return !r.filed && !r.unreadable;
	if (f === 'no-overview') return !r.overview;
	if (f === 'not-cited') return r.cited === 0;
	if (f === 'proposed') return r.proposed > 0;
	if (f === 'verified') return r.verified > 0;
	return true;
}

/** Whether `r` matches a search: every word of `q` in its key, title or authors. */
export function matches(r: LedgerRow, q: string): boolean {
	return q
		.toLowerCase()
		.split(/\s+/)
		.filter(Boolean)
		.every((w) => r.text.includes(w));
}

/** One result of a work as its Info lists it: its state, whether the person's text leans on it, and the section of the paper it stands in. */
export interface WorkResult {
	id: string;
	state: 'extracted' | 'verified' | 'proposed';
	/** The person's own text reaches it. */
	used: boolean;
	/** Its innermost numbered section, `1.1 · Algebras associated to pairs`; '' for one in none, such as the standing assumptions. */
	section: string;
}

/** Which of a work's results Info shows: all of them, those the person's text uses, those they verified, or those waiting as proposals. */
export type ResultFilter = 'all' | 'used' | 'verified' | 'proposed';

/**
 * A work's results in the paper's order, each with its section: the digest's, then any proposal the digest does not hold.
 *
 * Parameters
 * ----------
 * m : Manifest
 * ref : Reference
 * reached : Set<string>
 *     The external keys the person's own text reaches (`reachedExternal`).
 *
 * Returns
 * -------
 * WorkResult[]
 *     A discarded result is left out; a digest result with no record counts as extracted, a proposal with none as proposed.
 */
export function workResults(m: Manifest, ref: Reference, reached: Set<string>): WorkResult[] {
	// a section node lists its results and its subsections, so the section a result is a child of is its innermost; an unnumbered one is the digest's own, such as the opening it copies, and heads nothing
	const section = new Map<string, string>();
	for (const [id, n] of Object.entries(m.nodes)) {
		if (n.kind !== 'section' || n.digest !== ref.citekey) continue;
		const num = /-sec-([\d.]+)$/.exec(id)?.[1];
		if (!num) continue;
		const head = [num, n.title].filter(Boolean).join(' · ');
		for (const c of n.children ?? []) if (m.nodes[c]?.kind !== 'section') section.set(c, head);
	}
	const digest = ref.digest?.nodes ?? [];
	const ids = [...digest, ...(ref.proposed?.nodes ?? []).filter((id) => !digest.includes(id))];
	const out: WorkResult[] = [];
	for (const id of ids) {
		const state = ref.results?.[id]?.state ?? (digest.includes(id) ? 'extracted' : 'proposed');
		if (shownState(state)) out.push({ id, state, used: reached.has(id), section: section.get(id) ?? '' });
	}
	return out;
}

/** Whether a result in this state is listed: a discarded one is not. */
function shownState(s: string): s is WorkResult['state'] {
	return s === 'extracted' || s === 'verified' || s === 'proposed';
}

/** The results `f` keeps. */
export function filterResults(rs: WorkResult[], f: ResultFilter): WorkResult[] {
	if (f === 'all') return rs;
	return rs.filter((r) => (f === 'used' ? r.used : r.state === f));
}

/** The filters worth offering, with their counts: each that keeps some results but not all of them, after `all`; none when no filter would narrow the list. */
export function resultFilters(rs: WorkResult[]): { filter: ResultFilter; count: number }[] {
	const narrow = (['used', 'verified', 'proposed'] as const)
		.map((filter) => ({ filter, count: filterResults(rs, filter).length }))
		.filter((x) => x.count > 0 && x.count < rs.length);
	return narrow.length ? [{ filter: 'all', count: rs.length }, ...narrow] : [];
}

/** Results in runs of one section each, in order, so a heading stands above each run. */
export function bySection(rs: WorkResult[]): { section: string; results: WorkResult[] }[] {
	const out: { section: string; results: WorkResult[] }[] = [];
	for (const r of rs) {
		const last = out[out.length - 1];
		if (last && last.section === r.section) last.results.push(r);
		else out.push({ section: r.section, results: [r] });
	}
	return out;
}

/**
 * The person's documents that cite a work, each with the keys in it that do: what Info lists under "Cited in your documents".
 *
 * Parameters
 * ----------
 * m : Manifest
 * ref : Reference
 *
 * Returns
 * -------
 * { doc: string; keys: string[] }[]
 *     A document by its path, in the manifest's order of documents; an agent's document is not the person's and is left out. A citation from a document's own prose names no key.
 */
export function citedIn(m: Manifest, ref: Reference): { doc: string; keys: string[] }[] {
	const own = m.masters.filter((x) => !isAgentDocument(x)).map((x) => x.path);
	const docs = new Map<string, string[]>();
	const add = (doc: string, key?: string) => {
		if (!own.includes(doc)) return;
		const keys = docs.get(doc) ?? [];
		if (key && !keys.includes(key)) keys.push(key);
		docs.set(doc, keys);
	};
	for (const by of ref.cited_by ?? []) {
		if (own.includes(by)) {
			add(by);
			continue;
		}
		const node = m.nodes[by] ?? m.nodes[m.keys?.[by]?.node ?? ''];
		if (!node || node.derived_of) continue;
		for (const doc of node.reached_by ?? []) add(doc, by);
	}
	return own.filter((d) => docs.has(d)).map((doc) => ({ doc, keys: docs.get(doc)! }));
}
