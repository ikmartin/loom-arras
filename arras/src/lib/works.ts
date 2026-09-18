// A cited work's way out of the viewer: its identifiers as links to the services that resolve them, and a fetched copy when there is one. Also the one place a bibliography's TeX markup is made readable.
import { artifactUrl } from '$lib/paths';

import type { Reference } from '$lib/manifest/types';

export interface WorkLink {
	/** What the link reads as: `doi`, `arXiv`, `MR`, `zbMATH`, `link` or `PDF`. */
	label: string;
	href: string;
	/** The identifier itself, for a title attribute. */
	id: string;
}

/** The resolver for one `scheme:value` identifier, or null for a scheme nothing resolves (`work:`, a local hash). */
export function resolve(id: string): WorkLink | null {
	const at = id.indexOf(':');
	if (at < 1) return null;
	const scheme = id.slice(0, at).toLowerCase();
	const value = id.slice(at + 1).trim();
	if (!value) return null;
	switch (scheme) {
		case 'doi':
			return { label: 'doi', href: 'https://doi.org/' + value, id };
		case 'arxiv':
			return { label: 'arXiv', href: 'https://arxiv.org/abs/' + value, id };
		case 'mr':
			return { label: 'MR', href: 'https://mathscinet.ams.org/mathscinet-getitem?mr=' + value.replace(/^MR/i, ''), id };
		case 'zbl':
			return { label: 'zbMATH', href: 'https://zbmath.org/?q=an:' + value, id };
		default:
			return null;
	}
}

/**
 * Every outward link for a reference, in the order a reader wants them: the work's identifiers, a URL the bibliography gives, then a fetched PDF.
 *
 * Identifiers come from `works`; a manifest written before those fields existed still yields links from the bibliography's own `doi` and `eprint`. A PDF is offered only when the manifest says one has been fetched, since the directory is not in version control and another reader's copy may not have it.
 */
export function workLinks(ref: Reference): WorkLink[] {
	const ids = ref.works?.length ? ref.works : ref.work ? [ref.work] : fromBib(ref.bib);
	const out: WorkLink[] = [];
	const seen = new Set<string>();
	const add = (l: WorkLink | null) => {
		if (l && !seen.has(l.href)) {
			seen.add(l.href);
			out.push(l);
		}
	};
	for (const id of ids) add(resolve(id));
	const url = typeof ref.bib.url === 'string' ? ref.bib.url.trim() : '';
	if (/^https?:\/\//.test(url)) add({ label: 'link', href: url, id: url });
	if (ref.artifacts?.pdf) add({ label: 'PDF', href: artifactUrl(ref.artifacts.dir), id: ref.artifacts.dir });
	return out;
}

function fromBib(bib: Reference['bib']): string[] {
	const ids: string[] = [];
	if (typeof bib.doi === 'string' && bib.doi) ids.push('doi:' + bib.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, ''));
	if (typeof bib.eprint === 'string' && bib.eprint) ids.push('arxiv:' + bib.eprint);
	return ids;
}

const ACCENTS: Record<string, string> = { "'": '́', '`': '̀', '^': '̂', '"': '̈', '~': '̃', '=': '̄', '.': '̇', u: '̆', v: '̌', H: '̋', c: '̧', k: '̨' };
const LETTERS: Record<string, string> = { o: 'ø', O: 'Ø', ss: 'ß', ae: 'æ', AE: 'Æ', oe: 'œ', OE: 'Œ', aa: 'å', AA: 'Å', l: 'ł', L: 'Ł', i: 'ı' };

/**
 * A bibliography field as a reader should see it.
 *
 * BibTeX protects capitals with braces — `{{Gromov}}–{{Witten}}` — and writes accents as commands — `Sch\'emas` — and both were shown verbatim. Accent commands become the accented letter, the named letters (`\o`, `\ss`) become theirs, `--` becomes an en dash, and the remaining braces go. Mathematics in `$…$` is left for the typesetter.
 */
export function bibText(s: string | number | undefined): string {
	if (s === undefined || s === null) return '';
	// odd pieces are `$…$` spans, which pass through untouched
	return String(s)
		.split(/(\$[^$]*\$)/)
		.map((piece, i) => (i % 2 ? piece : prose(piece)))
		.join('')
		.normalize('NFC')
		.replace(/\s+/g, ' ')
		.trim();
}

function prose(text: string): string {
	let t = text;
	// font commands keep their argument: `\textit{Stacks Project}` reads `Stacks Project`
	t = t.replace(/\\(?:textit|textbf|textsc|textsf|texttt|textrm|emph|mathrm|mbox)\s*\{([^{}]*)\}/g, '$1');
	t = t.replace(/\\([`'^"~=.])\s*\{?\s*(\\i|[A-Za-z])\s*\}?/g, (_, acc: string, ch: string) => (ch === '\\i' ? 'i' : ch) + ACCENTS[acc]);
	t = t.replace(/\\([uvHck])\s*\{\s*(\\i|[A-Za-z])\s*\}/g, (_, acc: string, ch: string) => (ch === '\\i' ? 'i' : ch) + ACCENTS[acc]);
	t = t.replace(/\\(ss|ae|AE|oe|OE|aa|AA|o|O|l|L|i)(?![A-Za-z])\s?/g, (_, name: string) => LETTERS[name]);
	t = t.replace(/\\&/g, '&').replace(/---/g, '—').replace(/--/g, '–').replace(/~/g, ' ');
	return t.replace(/(?<!\\)[{}]/g, '');
}
