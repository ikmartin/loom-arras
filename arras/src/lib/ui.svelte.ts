// Viewer-side UI state that several components share: the selected annotation and the filters on annotation lists. Per-viewer conveniences only; nothing here is written anywhere.
class UiState {
	activeAnnotation = $state<string>('');
	kindFilter = $state<string>('');
	authorFilter = $state<string>('');
	showDiscarded = $state(false);
}

export const ui = new UiState();
