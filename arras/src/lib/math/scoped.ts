/** Math for an accepted comparison uses its saved preamble, independently of the live document. */
import { mathjax } from 'mathjax-full/js/mathjax.js';
import { TeX } from 'mathjax-full/js/input/tex.js';
import { SVG } from 'mathjax-full/js/output/svg.js';
import { browserAdaptor } from 'mathjax-full/js/adaptors/browserAdaptor.js';
import { RegisterHTMLHandler } from 'mathjax-full/js/handlers/html.js';
import { AllPackages } from 'mathjax-full/js/input/tex/AllPackages.js';
import type { Macro } from '$lib/manifest/types';

let registered = false;

function source(item: Element): string {
	const text = item.textContent?.trim() ?? '';
	if (text.startsWith('\\(') && text.endsWith('\\)')) return text.slice(2, -2);
	if (text.startsWith('\\[') && text.endsWith('\\]')) return text.slice(2, -2);
	return text;
}

export async function typesetScoped(root: Element, macros: Macro[]): Promise<void> {
	if (!registered) {
		RegisterHTMLHandler(browserAdaptor());
		registered = true;
	}
	const configured = Object.fromEntries(macros.map((m) => [m.name, m.args > 0 ? [m.body, m.args] : m.body]));
	const document = mathjax.document(window.document, {
		InputJax: new TeX({ packages: AllPackages, macros: configured, tags: 'none' }),
		OutputJax: new SVG({ fontCache: 'none' })
	});
	for (const item of root.querySelectorAll<HTMLElement>('.math')) {
		if (item.querySelector('mjx-container')) continue;
		const rendered = document.convert(source(item), { display: item.classList.contains('display') });
		item.replaceChildren(rendered as Node);
	}
}
