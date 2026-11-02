// LaTeX's auxiliary files: what a compile writes beside its document for its own next run -- the cross-references, the log, the bibliography's working files, the index's, SyncTeX's -- which a reader of the project's tree rarely wants to see. The tree leaves them out unless the reader turns that off in Settings. The compiled PDF is the document's output, not auxiliary, and stays.

const AUX =
	/\.(?:aux|log|out|toc|lof|lot|loa|bbl|blg|bcf|run\.xml|fls|fdb_latexmk|synctex|synctex\.gz|synctex\(busy\)|nav|snm|vrb|xdv|dvi|idx|ind|ilg|glo|gls|glg|ist|acn|acr|alg|thm|brf|spl|ptc|maf|mtc\d*|nlo|nls|xref|4ct|4tc|lg|tmp|auxlock)$|-blx\.bib$/i;

/** Whether the file at `path` is one LaTeX writes for its own next run. */
export function isAux(path: string): boolean {
	return AUX.test(path.slice(path.lastIndexOf('/') + 1));
}
