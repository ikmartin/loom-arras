// Viewer-side UI state that several components share: the selected annotation, and whether settled annotations are drawn. Per-viewer conveniences only, held for the session; nothing here is written anywhere.
class UiState {
	activeAnnotation = $state<string>('');
	/** Whether settled (resolved or discarded) annotations are drawn on the text and the page, faintly; off at rest (book 15.3.1). Every fragment and paper puts `show-settled` on itself while this is on. */
	showSettled = $state(false);
}

export const ui = new UiState();
