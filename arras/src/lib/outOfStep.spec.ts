import { describe, expect, it } from 'vitest';
import { stepFor } from './outOfStep.svelte';

const caps = { write_api: 1, capabilities: [] };

describe('a page out of step with the loom serving it', () => {
	it('says to restart when loom was updated under the server, to reload when the page is older than what it serves, and nothing otherwise', () => {
		expect(stepFor(null, 'v1', false)).toBeNull();
		expect(stepFor({ ...caps, viewer: 'v1', stale: false }, 'v1', false)).toBeNull();
		expect(stepFor({ ...caps, viewer: 'v2', stale: false }, 'v1', false)).toBe('reload');
		expect(stepFor({ ...caps, viewer: 'v1', stale: true }, 'v1', false)).toBe('restart');
		// a server that names no viewer, or a page that knows none, is never told to reload
		expect(stepFor({ ...caps }, 'v1', false)).toBeNull();
		expect(stepFor({ ...caps, viewer: 'v2' }, '', false)).toBeNull();
	});
});
