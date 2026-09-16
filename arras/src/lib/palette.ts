// The command palette is arras's search (book 15.2). The shells offer a search affordance and the palette owns the element, so the opener is registered here rather than passed down a tree.

let opener: (() => void) | null = null;

export function registerPalette(fn: (() => void) | null): void {
	opener = fn;
}

export function openPalette(): void {
	opener?.();
}
