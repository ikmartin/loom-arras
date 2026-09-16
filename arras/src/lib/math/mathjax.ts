// MathJax 3, TeX input and SVG output, bundled from the mathjax package so nothing loads from a CDN and a deployed site works offline. Macros come from the manifest at startup; a fragment naming a per-fragment set gets those definitions applied before its math is typeset.
import type { Macro } from '$lib/manifest/types';

type MJ = {
	typesetPromise: (els: Element[]) => Promise<void>;
	typesetClear: (els: Element[]) => void;
	startup: { promise: Promise<void> };
	texReset?: () => void;
};

declare global {
	interface Window {
		MathJax: unknown;
	}
}

let loaded: Promise<MJ> | null = null;
let currentMacros: Record<string, string | [string, number]> = {};

function toConfig(macros: Macro[]): Record<string, string | [string, number]> {
	const out: Record<string, string | [string, number]> = {};
	for (const m of macros) out[m.name] = m.args > 0 ? [m.body, m.args] : m.body;
	return out;
}

export function ensureMathJax(macros: Macro[]): Promise<MJ> {
	if (!loaded) {
		currentMacros = toConfig(macros);
		window.MathJax = {
			tex: {
				inlineMath: [['\\(', '\\)']],
				displayMath: [['\\[', '\\]']],
				processEscapes: true,
				packages: { '[+]': ['ams', 'amscd', 'boldsymbol', 'mathtools', 'newcommand', 'color', 'cancel', 'bbox', 'html', 'unicode', 'verb', 'mhchem', 'physics', 'textmacros'] },
				macros: currentMacros,
				tags: 'none'
			},
			svg: { fontCache: 'local' },
			options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] },
			startup: { typeset: false }
		};
		// the full component carries every TeX extension, so \color and friends never trigger a runtime load from a path that does not exist offline
		loaded = import('mathjax/es5/tex-svg-full.js').then(async () => {
			const mj = window.MathJax as MJ;
			await mj.startup.promise;
			return mj;
		});
	}
	return loaded;
}

function macroPrefix(macros: Macro[]): string {
	return macros.map((m) => (m.args > 0 ? `\\renewcommand{\\${m.name}}[${m.args}]{${m.body}}` : `\\renewcommand{\\${m.name}}{${m.body}}`)).join('');
}

export async function typeset(el: Element, defaults: Macro[], perFragment: Macro[] = []): Promise<void> {
	const mj = await ensureMathJax(defaults);
	if (perFragment.length) {
		const prefix = macroPrefix(perFragment);
		const first = el.querySelector('.math');
		if (first) first.textContent = prefix + (first.textContent ?? '');
	}
	await mj.typesetPromise([el]);
}
