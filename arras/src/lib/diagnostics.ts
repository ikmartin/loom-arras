// Diagnostics as Review › Problems reads them: whose each is to fix, what is wrong in words, and where to open it. Unknown codes are titled by their message; nothing here fails on a code it has never seen.
import type { Diagnostic, Fix, Manifest } from './manifest/types';
import { keyTarget, placeUrl } from './nav';
import { pathFor } from './workspace/item';

/** Whose a diagnostic is to fix: the person's, an agent's copy's, or a cited work's, whose digest loom wrote. A publisher that does not say makes every one the person's. */
export type Owner = 'person' | 'copy' | 'work';

export function ownerOf(d: Diagnostic): Owner {
	return d.owner === 'copy' ? 'copy' : d.owner === 'work' ? 'work' : 'person';
}

/** What each code says is wrong, in words, by the code's name after any publisher's namespace (`ns:name`), so the table names no publisher; `name severity` where one code says two things. Two codes that say one thing share a title, and so a group. */
const TITLES: Record<string, string> = {
	'duplicate-id': 'Defined twice',
	'duplicate-label': 'Defined twice',
	'dangling-link': 'A reference points nowhere',
	'missing-include': 'An included file is missing',
	'double-inclusion': 'A file is included twice',
	'inclusion-cycle': 'Files include each other in a circle',
	unreachable: 'In no document',
	'reference-to-loose': 'A reference to a block no document includes',
	'environment-spans-files': 'An environment opens in one file and closes in another',
	'line-anchoring': 'A \\begin or \\end shares its line',
	'unknown-environment': 'An environment the preamble does not declare',
	'unattached-proof': 'A proof belongs to no result',
	'multi-target-proof': 'A proof names several results',
	'macros-unloaded': "The document does not load loom's macros",
	'macro-shadowed': "The preamble redefines one of loom's macros",
	'macros-missing': 'loom.sty is missing',
	'taxon-conflict': 'Documents disagree on what an environment is',
	'prefix-is-citekey': 'The id prefix is also a citation key',
	'unknown-directive': 'An unknown % !LOOM line',
	'invalid-name': 'A name that cannot be used',
	'unlabelled-node': 'A result has no id',
	'positional-proof-key': 'A result has several unlabelled proofs',
	'unexpected-proof': 'A proof of something that needs none',
	'missing-proof': 'A result has no proof',
	'needs-classification': 'A block needs its basis said',
	'misplaced-basis': 'A basis line outside a block',
	'equation-in-proof-referenced': 'Another block cites an equation inside a proof',
	'uses-missing': 'A proof cites something its \\uses does not list',
	'uses-unused': 'A \\uses entry the proof never mentions',
	'see-redundant': 'A see line repeats itself',
	'dependency-cycle': 'Results depend on each other in a circle',
	'cites-proposed-node': 'A citation of a block not yet verified',
	'snippet-failed': 'TeX could not make a text, shown as its source',
	'closure-failed': 'A block does not compile on its own',
	'import-outside-tree': 'An imported file lies outside the paper',
	'non-utf8-source': 'A file is not UTF-8',
	'unknown-theoremstyle': 'An unknown theorem style',
	'taxon-name-macro': 'An environment named by an undefined macro',
	'citekey-slug-collision': 'Two citation keys share a digest prefix',
	'main-not-found': 'The default document is not a document',
	'main-unset': 'No default document',
	'unknown-config-key': 'An unknown setting',
	'retired-ledger-key': 'An acceptance of a block that is gone',
	'detached-annotation': 'Annotations lost their place',
	'previous-key-match': 'An acceptance matches a renamed proof',
	'foreign-annotations': 'An unreadable line in the annotation log',
	'unmatched-postnote': 'A citation names a result its digest lacks',
	'undigested-citekey': 'A cited work has no digest',
	'postnote-from-another-version': 'A citation answered by another version of the work',
	'unresolved-work': 'A cited work has no identifier',
	'unverified-locators': "A digest's numbers may not be the published ones",
	'version-mismatch': 'A digest of another version',
	'missing-package': 'A digest needs a package the preamble lacks',
	'digest-without-bib': 'A digest of a work the bibliography lacks',
	'no-readable-copy': 'No copy of the work to read',
	'superseded-file': 'A document a conversion replaced',
	'history-missing': 'Part of the history is gone',
	'history-edited': 'The history was edited by hand',
	'history-corrupt': 'The history cannot be read',
	'history-interrupted': 'A step was interrupted',
	'dangling-ancestry': 'The history names a step it no longer has',
	'id-reused': 'A retired id is used again',
	'node-recovered': 'A retired id is back with its old text',
	'no-live-document': 'No document of yours',
	'derived-id-in-person-document': "An agent's id in your document",
	'agent-document-unrecorded': "An agent's copy with no record of its making",
	'plain-id-in-agent-document': "A plain id in an agent's copy",
	'agent-permissions-stale': "Claude Code's permissions are out of date",
	'home-missing': 'The home page is missing',
	'document-gone': 'A document is gone'
};

/** What `d` says is wrong: its code's title at its severity, else its code's, else its message. */
export function titleOf(d: Pick<Diagnostic, 'code' | 'message' | 'severity'>): string {
	const name = d.code.replace(/^[^:]*:/, '');
	return TITLES[`${name} ${d.severity}`] ?? TITLES[name] ?? d.message;
}

export interface Group {
	title: string;
	/** Every code in the group, in the order met. */
	codes: string[];
	severity: string;
	items: Diagnostic[];
}

const ORDER: Record<string, number> = { error: 0, warning: 1, info: 2 };

/** Diagnostics by what is wrong, worst first; within a severity, the larger group first. */
export function groupProblems(items: Diagnostic[]): Group[] {
	const map = new Map<string, Group>();
	for (const d of items) {
		const title = titleOf(d);
		let g = map.get(title);
		if (!g) map.set(title, (g = { title, codes: [], severity: d.severity, items: [] }));
		g.items.push(d);
		if (!g.codes.includes(d.code)) g.codes.push(d.code);
		if ((ORDER[d.severity] ?? 3) < (ORDER[g.severity] ?? 3)) g.severity = d.severity;
	}
	return [...map.values()].sort((a, b) => (ORDER[a.severity] ?? 3) - (ORDER[b.severity] ?? 3) || b.items.length - a.items.length || a.title.localeCompare(b.title));
}

/** The four parts of Problems: the person's errors and warnings, an agent's copy's, the cited works', and every remark. */
export interface Parts {
	yours: Diagnostic[];
	copy: Diagnostic[];
	works: Diagnostic[];
	remarks: Diagnostic[];
}

export function partsOf(items: Diagnostic[]): Parts {
	const out: Parts = { yours: [], copy: [], works: [], remarks: [] };
	for (const d of items) {
		if (d.severity === 'info') out.remarks.push(d);
		else if (ownerOf(d) === 'copy') out.copy.push(d);
		else if (ownerOf(d) === 'work') out.works.push(d);
		else out.yours.push(d);
	}
	return out;
}

/** The person's errors and warnings: what Problems counts. */
export function yoursCount(m: Pick<Manifest, 'diagnostics'>): number {
	return partsOf(m.diagnostics).yours.length;
}

/** The work a cited work's diagnostic is about: the work its fix digests again, else its results' digest, else the digest its location is in, else '' when it says none. */
export function workOf(m: Pick<Manifest, 'nodes'>, d: Diagnostic): string {
	const act = d.fixes?.find((f) => f.act?.endpoint === 'library-update')?.act;
	const named = (act?.body as { works?: unknown } | undefined)?.works;
	if (Array.isArray(named) && typeof named[0] === 'string') return named[0];
	for (const k of d.keys) if (m.nodes[k]?.digest) return m.nodes[k].digest!;
	for (const l of d.locations) {
		const n = Object.values(m.nodes).find((x) => x.file === l.file && x.digest);
		if (n) return n.digest!;
	}
	return '';
}

/** The cited works' diagnostics by work, in their order; a diagnostic naming no work is under ''. */
export function byWork(m: Pick<Manifest, 'nodes'>, items: Diagnostic[]): { work: string; items: Diagnostic[] }[] {
	const map = new Map<string, Diagnostic[]>();
	for (const d of items) {
		const w = workOf(m, d);
		if (!map.has(w)) map.set(w, []);
		map.get(w)!.push(d);
	}
	return [...map.entries()].map(([work, xs]) => ({ work, items: xs })).sort((a, b) => b.items.length - a.items.length || a.work.localeCompare(b.work));
}

/** Where `d` is read: its first key's place, else its first location's file at the line, else nothing. A file the viewer does not show (loom's own) has no place. */
export function openUrl(m: Manifest, d: Diagnostic): string {
	const key = d.keys.find((k) => keyTarget(m, k));
	if (key) return placeUrl(m, key);
	const loc = d.locations.find((l) => m.files?.some((f) => f.path === l.file));
	return loc ? lineUrl(m, loc.file, loc.line) : '';
}

/** A shown file at one line. */
export function lineUrl(m: Manifest, path: string, line: number): string {
	return pathFor(m, { kind: 'file', id: path, anchor: `L${line}` });
}

/** The fixes a viewer acts on itself, by the endpoint each names, and those it offers as a command to copy. */
export function splitFixes(d: Diagnostic): { acts: Fix[]; commands: Fix[] } {
	const fixes = d.fixes ?? [];
	return { acts: fixes.filter((f) => f.act), commands: fixes.filter((f) => !f.act) };
}

export function countBySeverity(items: Diagnostic[]): Record<string, number> {
	const out: Record<string, number> = {};
	for (const d of items) out[d.severity] = (out[d.severity] ?? 0) + 1;
	return out;
}
