// The manifest store: one loaded manifest, its hash, and a poll that re-fetches with If-None-Match. Re-rendering follows the hash; nothing else ever triggers it (spec README, viewer obligation 3).
import { loadManifest, type Loaded } from './loader';
import type { Diagnostic, Manifest } from './types';

class ManifestStore {
	manifest = $state<Manifest | null>(null);
	hash = $state<string>('');
	problem = $state<Diagnostic | null>(null);
	loading = $state(true);
	polls = $state(0);
	#etag: string | null = null;
	#timer: ReturnType<typeof setInterval> | null = null;
	url = '/build/manifest.json';

	async refresh(): Promise<void> {
		try {
			const r = await loadManifest(this.url, this.#etag);
			this.polls += 1;
			if (r === 'unchanged') return;
			if (r.manifest === null) {
				this.problem = r.diagnostic;
				this.manifest = null;
				this.hash = '';
				return;
			}
			const loaded = r as Loaded;
			if (loaded.hash !== this.hash) {
				this.manifest = loaded.manifest;
				this.hash = loaded.hash;
				this.problem = null;
			}
			this.#etag = loaded.etag;
		} catch (err) {
			this.problem = {
				severity: 'error',
				code: 'arras:manifest-missing',
				message: `could not fetch the manifest: ${(err as Error).message}`,
				locations: [],
				keys: []
			};
		} finally {
			this.loading = false;
		}
	}

	start(intervalMs = 1000): void {
		void this.refresh();
		if (this.#timer === null && intervalMs > 0) {
			// a tab nobody is looking at has nothing to re-render, so it stops asking, and asks at once when it is looked at again
			this.#timer = setInterval(() => {
				if (globalThis.document?.visibilityState !== 'hidden') void this.refresh();
			}, intervalMs);
			globalThis.document?.addEventListener('visibilitychange', this.#onVisible);
		}
	}

	#onVisible = () => {
		if (document.visibilityState === 'visible') void this.refresh();
	};

	stop(): void {
		if (this.#timer !== null) {
			clearInterval(this.#timer);
			this.#timer = null;
			globalThis.document?.removeEventListener('visibilitychange', this.#onVisible);
		}
	}
}

export const store = new ManifestStore();
