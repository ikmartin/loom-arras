// Where a project file opens, the way the tree opens it: the research state as its page, a document as itself, an included `.tex` file as the document that reads it at its place, and every other file as a file.
import type { Manifest, ProjectFile } from '$lib/manifest/types';
import { masterUrl } from '$lib/nav';
import { route } from '$lib/paths';
import { itemForFile, pathFor } from '$lib/workspace/item';

export function fileHref(m: Manifest, f: ProjectFile): string {
	if (f.path === m.research_state?.path) return route('/page/state');
	if (f.kind === 'document') return masterUrl(f.path);
	return pathFor(m, itemForFile(m, f.path));
}
