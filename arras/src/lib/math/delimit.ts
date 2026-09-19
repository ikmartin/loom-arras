// A LaTeX statement's dollar delimiters in the form the publisher emits and MathJax is configured for.

/** `$$…$$` to `\[…\]` first, so the inline rule cannot split a display in two, then `$…$` to `\(…\)`; an escaped `\$` is a dollar sign and stays. */
export function delimit(tex: string): string {
	return tex
		.replace(/(?<!\\)\$\$([\s\S]*?)(?<!\\)\$\$/g, (_, m: string) => '\\[' + m + '\\]')
		.replace(/(?<!\\)\$([^$]+?)(?<!\\)\$/g, (_, m: string) => '\\(' + m + '\\)');
}
