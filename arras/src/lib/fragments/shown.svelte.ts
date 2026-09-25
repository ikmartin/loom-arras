// Whether the annotations on a document are open, shared between the fragment that draws them and a rail that offers to open them. The fragment owns the doing -- it is what holds the mounted boxes -- and registers the two actions here; a page with a rail of its own reads `allOpen` to say which way its control goes.
//
// `ready` is not the same as "there are annotations": it is whether a fragment is showing any right now, so the control is absent on a document with nothing to open rather than present and inert.

export class Annotations {
	allOpen = $state(false);
	ready = $state(false);

	expand: () => void = () => {};
	collapse: () => void = () => {};

	toggle(): void {
		if (this.allOpen) this.collapse();
		else this.expand();
	}
}
