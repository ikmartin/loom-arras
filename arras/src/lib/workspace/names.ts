// Short names for results, as a reader refers to them in a tab: `Prop 2.1`, not `Proposition 2.1, p.~1`.

/** The abbreviations loom's digest ids use (`Arden24-prop-2.1`), capitalised as a reader writes them. */
const SHORT: Record<string, string> = {
	theorem: 'Thm',
	lemma: 'Lem',
	proposition: 'Prop',
	corollary: 'Cor',
	definition: 'Def',
	remark: 'Rem',
	example: 'Ex',
	conjecture: 'Conj',
	construction: 'Constr'
};

/**
 * A digest locator as a tab names it: the postnote's page dropped and the leading taxon abbreviated.
 *
 * `Proposition 2.1, p.~1` is `Prop 2.1`; a locator that names no taxon (`Standing assumptions`) is kept as written, less its page.
 */
export function shortLocator(locator: string): string {
	const bare = locator
		.replace(/,?\s*(?:pp?\.|pages?)\s*~?\s*[\d–-]+\s*$/i, '')
		.replace(/~/g, ' ')
		.trim();
	const m = /^([A-Za-z]+)\b(.*)$/.exec(bare);
	const short = m ? SHORT[m[1].toLowerCase()] : undefined;
	return short ? `${short}${m![2]}` : bare;
}

/** What `nodeName` and `keyName` read of the manifest. */
interface Named {
	masters: { path: string; default?: boolean }[];
	nodes: Record<string, { kind?: string; taxon: string; title?: string | null; numbers: Record<string, { number: string }>; digest?: string | null; locator?: string | null }>;
	keys?: Record<string, { node?: string }>;
	regions?: Record<string, { container: string; label: string; numbers: Record<string, { number: string }> }>;
	references?: Record<string, { citekey: string; work?: string | null; works?: string[] }>;
}

/**
 * A result as a reader refers to it in a list: its taxon and number where the default document numbers it, a result read off a cited work by the work and its short name, else its taxon and title, else its id.
 *
 * A proof is named for the result it proves.
 */
export function nodeName(m: Named, id: string): string {
	const n = m.nodes[id];
	if (!n) return id;
	const owner = m.keys?.[id]?.node;
	if (n.kind === 'proof' && owner && owner !== id) return `proof of ${nodeName(m, owner)}`;
	if (n.digest && n.locator) return `${n.digest} · ${shortLocator(n.locator)}`;
	const main = m.masters.find((x) => x.default)?.path;
	const number = main ? n.numbers[main]?.number : undefined;
	if (number) return `${n.taxon} ${number}`;
	return n.title ? `${n.taxon} · ${n.title}` : id;
}

/**
 * Any key a session or a context names, as a reader would: a document by its file, a result by `nodeName`, an unlabelled proof as the proof of its result, an equation by its number in its result, a cited work's identifier by its citekey; anything else as itself.
 *
 * Callers keep the key itself as the name's title, so nothing is hidden by the shortening.
 */
export function keyName(m: Named, key: string): string {
	if (m.masters.some((x) => x.path === key)) return key.split('/').pop() ?? key;
	if (m.nodes[key]) return nodeName(m, key);
	const region = m.regions?.[key];
	if (region) {
		const main = m.masters.find((x) => x.default)?.path ?? '';
		const number = region.numbers[main]?.number;
		return `${number ? `(${number})` : region.label} in ${nodeName(m, region.container)}`;
	}
	const owner = m.keys?.[key]?.node;
	if (owner && owner !== key) return `proof of ${nodeName(m, owner)}`;
	const work = Object.values(m.references ?? {}).find((r) => r.work === key || r.works?.includes(key));
	return work ? work.citekey : key;
}
