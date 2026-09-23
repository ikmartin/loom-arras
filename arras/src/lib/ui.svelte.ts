// Viewer-side UI state that several components share: the selected annotation. Per-viewer conveniences only; nothing here is written anywhere.
class UiState {
	activeAnnotation = $state<string>('');
}

export const ui = new UiState();
