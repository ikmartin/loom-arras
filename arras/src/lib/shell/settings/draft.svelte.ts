// The one draft of the quilt's settings, kept while the window is closed so a change is not lost by closing it. Save posts every change at once; a refusal names each setting it refused, shown beside that setting.

import { store } from '$lib/manifest/client.svelte';
import { write } from '$lib/write';
import { edited, pending, published, type Value } from './draft';

class Draft {
	edits = $state<Record<string, Value>>({});
	/** Why the publisher refused a setting, by key; the message when it refused the save as a whole. */
	refused = $state<Record<string, string>>({});
	message = $state('');
	busy = $state(false);

	readonly base = $derived(store.manifest?.config ? published(store.manifest.config) : {});
	/** The changes Save would write, less any the published config has caught up with. */
	readonly changes = $derived(pending(this.base, this.edits));
	readonly count = $derived(Object.keys(this.changes).length);

	value(key: string): Value | undefined {
		return key in this.changes ? this.changes[key] : this.base[key];
	}

	set(key: string, value: Value): void {
		this.edits = edited(this.base, this.changes, key, value);
		if (key in this.refused) {
			const { [key]: _, ...rest } = this.refused;
			this.refused = rest;
		}
	}

	revert(): void {
		this.edits = {};
		this.refused = {};
		this.message = '';
	}

	async save(): Promise<boolean> {
		this.busy = true;
		this.message = '';
		const answer = await write('settings-save', { changes: this.changes });
		if (answer.ok) {
			await store.refresh();
			this.revert();
		} else {
			this.refused = answer.error?.fields ?? {};
			this.message = answer.error?.fields ? 'Nothing was saved: fix the settings marked below.' : (answer.error?.message ?? 'Could not save config.toml');
		}
		this.busy = false;
		return answer.ok;
	}
}

export const draft = new Draft();
