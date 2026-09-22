// When a session was last touched, in the words a person uses (plan 0.13.1). One helper, shared by the panel and the
// discussion pane, so two surfaces cannot word the same interval differently.

const DAY = 86_400_000;
const WEEKDAY = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/**
 * A timestamp as a reader would say it: `today`, `yesterday`, a weekday inside the last week, then a date.
 *
 * Deliberately coarse. A session is a sitting, and the useful question is whether it is the one you were in this morning or one from before the weekend — never the minute it opened, which the permalink carries for anyone who needs it.
 */
export function when(stamp: string | undefined, now: Date = new Date()): string {
	if (!stamp) return '';
	const then = new Date(stamp);
	if (Number.isNaN(then.getTime())) return '';
	const midnight = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
	const days = Math.round((midnight(now) - midnight(then)) / DAY);
	if (days <= 0) return 'today';
	if (days === 1) return 'yesterday';
	if (days < 7) return WEEKDAY[then.getDay()];
	if (days < 14) return 'last week';
	return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/** The same interval, said of a session in the state it is in: `resumed today`, `closed last week`. */
export function touched(stamp: string | undefined, state: string, now: Date = new Date()): string {
	const said = when(stamp, now);
	if (!said) return '';
	return state === 'open' ? said : `closed ${said}`;
}
