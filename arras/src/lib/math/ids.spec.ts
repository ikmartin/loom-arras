import { describe, expect, it } from 'vitest';
import { idParts } from './ids';

const known = new Set(['rl-0020-ai', 'rl-001C-ai', 'rl-0003', 'rl-0004/proof']);
const parts = (s: string) => idParts(s, (k) => known.has(k));

describe('bare ids in prose', () => {
	it('are cut out of the text around them, suffixes and proofs included', () => {
		expect(parts('This invokes rl-0020-ai(a), and rl-001C-ai too.')).toEqual(['This invokes ', { id: 'rl-0020-ai' }, '(a), and ', { id: 'rl-001C-ai' }, ' too.']);
		expect(parts('see rl-0004/proof.')).toEqual(['see ', { id: 'rl-0004/proof' }, '.']);
	});
	it('leave unknown ids and parts of longer words alone', () => {
		expect(parts('rl-9999 is not a node')).toEqual(['rl-9999 is not a node']);
		expect(parts('lem:rl-0003 and xrl-0003y and rl-0003-b')).toEqual(['lem:rl-0003 and xrl-0003y and rl-0003-b']);
	});
});

it('recognizes numbered section-copy identities and qualified proof keys', () => {
 const known = new Set(['zk-0001-ai-01', 'zk-0001-ai-02/proof/2']);
 expect(idParts('Compare zk-0001-ai-01 with zk-0001-ai-02/proof/2.', key => known.has(key))).toEqual(['Compare ', {id:'zk-0001-ai-01'}, ' with ', {id:'zk-0001-ai-02/proof/2'}, '.']);
});
