// A short word at the foot of the window about something just done that left nothing on the page to show it, as Quote does: what was copied, and from where. One at a time, gone after a few seconds or a click.

export interface Said {
	title: string;
	/** The words it is about, set as a quotation. */
	words?: string;
	/** Lines beneath, in the chrome's face. */
	lines: string[];
}

export const toast = $state<{ said: Said | null }>({ said: null });

let timer: ReturnType<typeof setTimeout> | undefined;

/** Say `said` for seven seconds, in place of whatever was said before. */
export function say(said: Said): void {
	toast.said = said;
	clearTimeout(timer);
	timer = setTimeout(() => (toast.said = null), 7000);
}

/** Take it down now. */
export function unsay(): void {
	clearTimeout(timer);
	toast.said = null;
}
