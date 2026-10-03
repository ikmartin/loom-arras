// The manifest store: one loaded manifest, its hash, and a poll that re-fetches with If-None-Match. Re-rendering follows the hash; nothing else ever triggers it (spec README, viewer obligation 3).
import { dataUrl } from '$lib/paths';
import { loadManifest, type Loaded } from './loader';
import type { AdoptionReview, Diagnostic, Manifest } from './types';

class ManifestStore {
	manifest = $state<Manifest | null>(null);
	hash = $state<string>('');
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

	/** Apply the server acknowledgement immediately; late polls cannot regress its revision. */
	setAdoption(copy: string, fingerprint: string, choices: AdoptionReview['choices']): void {
		for (const c of this.manifest?.contributions ?? []) {
			if (c.kind === 'adopt' && c.copy === copy && c.fingerprint === fingerprint && (c.choices?.revision ?? 0) <= (choices.revision ?? 0)) c.choices = choices;
		}
	}

	async refresh(): Promise<void> {
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
				if (loaded.manifest.reviewer?.name === this.manifest?.reviewer?.name) {
					for (const old of this.manifest?.contributions ?? []) {
						if (old.kind !== 'adopt') continue;
						const next = loaded.manifest.contributions?.find(c => c.kind === 'adopt' && c.copy === old.copy);
						if (next?.kind === 'adopt' && next.fingerprint === old.fingerprint && (old.choices?.revision ?? 0) > (next.choices?.revision ?? 0)) next.choices = old.choices;
					}
				}
                const content = (m: Manifest) => JSON.stringify({...m, contributions: m.contributions?.map(c => c.kind === 'adopt' ? {...c, choices: undefined} : c)});
                if (this.manifest && content(this.manifest) === content(loaded.manifest)) {
                    for (const c of loaded.manifest.contributions ?? []) if (c.kind === 'adopt') this.setAdoption(c.copy, c.fingerprint, c.choices);
                } else this.manifest = loaded.manifest;
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
