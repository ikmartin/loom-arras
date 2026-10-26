// The one PDF viewer. Anything that links into a cited work opens it here rather than navigating away, so a reader checking a citation keeps their place.

import type { WorkLink } from '$lib/worklink';

class PdfState {
	link = $state.raw<WorkLink | null>(null);

	open(link: WorkLink): void {
		this.link = link;
	}

	close(): void {
		this.link = null;
	}
}

export const pdf = new PdfState();
