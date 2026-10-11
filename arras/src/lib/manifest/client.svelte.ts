// The manifest store: one loaded manifest, its hash, and a poll that re-fetches with If-None-Match, which the publisher's stream, where it offers one, makes only a fallback (stream.ts). Re-rendering follows the hash; nothing else ever triggers it (spec README, viewer obligation 3).
import { dataUrl } from '$lib/paths';
import { loadManifest, type Loaded } from './loader';
import { untrack } from 'svelte';
import type { Diagnostic, Macro, Manifest } from './types';

class ManifestStore {
	manifest = $state<Manifest | null>(null);
	hash = $state<string>('');
	/** The corpus's macros as text: equal across manifests that did not change them, so what depends on it does not run again on every rebuild. */
	#macroKey = $derived(JSON.stringify(this.manifest?.macros.default ?? []));
	/** The corpus's macros, read so that an effect follows a change of them rather than every new manifest. */
	get macros(): Macro[] {
		void this.#macroKey;
		return untrack(() => this.manifest?.macros.default ?? []);
	}
	problem = $state<Diagnostic | null>(null);
	loading = $state(true);
	polls = $state(0);
	#etag: string | null = null;
	#timer: ReturnType<typeof setInterval> | null = null;
	/** The manifest to poll. Follows the configured data root unless a host sets it outright. */
	url = '';

	get manifestUrl(): string {
		return this.url || dataUrl('manifest.json');
	}

	#running: Promise<void> | null = null;
	#again = false;

	/** Fetch the manifest if it changed. One fetch at a time: asked again while one is under way, it fetches once more after it, since what prompted the ask may be newer than the fetch in flight. */
	refresh(): Promise<void> {
		if (this.#running) {
			this.#again = true;
			return this.#running;
		}
		this.#running = (async () => {
			try {
				do {
					this.#again = false;
					await this.#load();
				} while (this.#again);
			} finally {
				this.#running = null;
			}
		})();
		return this.#running;
	}

	async #load(): Promise<void> {
		try {
			const r = await loadManifest(this.manifestUrl, this.#etag);
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
			this.#poll(intervalMs);
			globalThis.document?.addEventListener('visibilitychange', this.#onVisible);
		}
	}

	/** Poll every `intervalMs` from now on: slowly while the publisher's stream says when to fetch, and as often as before when it cannot. */
	pace(intervalMs: number): void {
		if (this.#timer === null) return;
		clearInterval(this.#timer);
		this.#poll(intervalMs);
	}

	#poll(intervalMs: number): void {
		// a tab nobody is looking at has nothing to re-render, so it stops asking, and asks at once when it is looked at again
		this.#timer = setInterval(() => {
			if (globalThis.document?.visibilityState !== 'hidden') void this.refresh();
		}, intervalMs);
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
