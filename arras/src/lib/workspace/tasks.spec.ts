import { describe, expect, it } from 'vitest';
import { onlyTicks, ticksIn } from './tasks';

const body = (first: boolean, second: boolean) => `<ul>
<li class="task" data-done="${first}" data-task="3:aa">one</li>
<li class="task" data-done="${second}" data-task="4:bb">two</li>
<li class="task" data-done="true">a notebook's, only drawn</li>
<li>not a task</li>
</ul>`;

describe('a body read for its boxes', () => {
	it('is the same body when only the ticks differ', () => {
		expect(onlyTicks(body(false, false), body(true, false))).toBe(true);
		expect(onlyTicks(body(false, false), body(false, false))).toBe(true);
	});

	it('is a different body when anything else differs', () => {
		expect(onlyTicks(body(false, false), body(false, false).replace('one', 'uno'))).toBe(false);
		expect(onlyTicks(body(false, false), body(false, false).replace('3:aa', '5:aa'))).toBe(false);
	});

	it('names each tickable box and leaves out one that is only drawn', () => {
		expect([...ticksIn(body(true, false))]).toEqual([
			['3:aa', true],
			['4:bb', false]
		]);
	});
});
