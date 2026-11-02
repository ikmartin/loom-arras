import { describe, expect, it } from 'vitest';
import type { QuiltSettings } from '$lib/manifest/types';
import { edited, pending, published, same } from './draft';

const config = {
	editable: ['quilt.name', 'library.online', 'agents.deny', 'quilt.home'],
	read_only: ['quilt.history'],
	quilt: { name: 'ring', main: '', home: '', prefix: 'r', engine: 'pdflatex', history: '.loom/history', research_state: 'research-state.md' },
	library: { online: false, contact: '' },
	lint: { disable: [], codes: [] },
	agents: { deny: ['paper/'], protected: [], layer: true, variant: 'mcp', stale: false, command: '', clients: [] },
	sync: { paired: false, command: 'x' },
	warnings: []
} as QuiltSettings;

describe('the draft of the quilt settings', () => {
	it('publishes only the keys the publisher lets Settings change', () => {
		expect(published(config)).toEqual({ 'quilt.name': 'ring', 'library.online': false, 'agents.deny': ['paper/'], 'quilt.home': '' });
	});

	it('counts a change back to the published value as no change', () => {
		const base = published(config);
		let edits = edited(base, {}, 'quilt.name', 'rings');
		edits = edited(base, edits, 'agents.deny', ['paper/', 'notes/']);
		expect(Object.keys(edits)).toEqual(['quilt.name', 'agents.deny']);
		edits = edited(base, edits, 'quilt.name', 'ring');
		edits = edited(base, edits, 'agents.deny', ['paper/']);
		expect(edits).toEqual({});
	});

	it('drops the edits the published config has caught up with', () => {
		const edits = { 'quilt.name': 'rings', 'library.online': true };
		const saved = published({ ...config, quilt: { ...config.quilt, name: 'rings' } });
		expect(pending(saved, edits)).toEqual({ 'library.online': true });
	});

	it('compares lists by their entries in order', () => {
		expect(same(['a', 'b'], ['a', 'b'])).toBe(true);
		expect(same(['a', 'b'], ['b', 'a'])).toBe(false);
		expect(same(['a'], 'a')).toBe(false);
		expect(same(true, true)).toBe(true);
	});
});
