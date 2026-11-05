// What a published Markdown body says of its boxes (specs/dialect.md §2.14), read as text so that a new publication can be compared with what is on the page before anything is drawn again.

const DONE = / data-done="(?:true|false)"/g;
const TASK = /<li class="task" data-done="(true|false)" data-task="([^"]+)"/g;

/** Whether two bodies differ only in which boxes are ticked, so that the page can keep what it has drawn, typeset mathematics and scroll position included. */
export function onlyTicks(drawn: string, next: string): boolean {
	return drawn.replace(DONE, '') === next.replace(DONE, '');
}

/** Each tickable box of a body by the id a tick sends back, with whether it is ticked. */
export function ticksIn(html: string): Map<string, boolean> {
	return new Map([...html.matchAll(TASK)].map((m) => [m[2], m[1] === 'true']));
}
