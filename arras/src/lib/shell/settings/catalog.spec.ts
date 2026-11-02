import { describe, expect, it } from 'vitest';
import { GROUPS, SECTIONS, SETTINGS } from './catalog';

describe('the settings catalog', () => {
	it('gives every setting a section that exists, and every section a setting', () => {
		const ids = new Set(SECTIONS.map((s) => s.id));
		for (const s of SETTINGS) expect(ids.has(s.section), s.id).toBe(true);
		for (const id of ids) expect(SETTINGS.some((s) => s.section === id), id).toBe(true);
	});

	it('lists Loom first, Profile at its head, then Quilt', () => {
		expect(GROUPS.map((g) => g.label)).toEqual(['Loom', 'Quilt']);
		expect(SECTIONS.filter((s) => s.group === 'loom').map((s) => s.label)).toEqual(['Profile', 'Appearance', 'Files']);
		// every section of a group stands together, in the groups' order
		const order = SECTIONS.map((s) => GROUPS.findIndex((g) => g.id === s.group));
		expect(order).toEqual([...order].sort((a, b) => a - b));
	});
});
