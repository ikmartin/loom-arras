// A line hung under a pane's toolbar: a question a control on the bar asks, with its buttons, or the answer to an act. A toolbar has one row of fixed height, so a sentence never fits on it; and an act that turns the pane to another item (a version restored turns to the live text) takes its control away, while the answer must stay to be read. Keyed by pane, so the toolbar of whatever the pane shows next draws it.

export interface StripAct {
	label: string;
	testid: string;
	primary?: boolean;
	run: () => void;
}

export interface Strip {
	text: string;
	testid: string;
	refused?: boolean;
	/** The buttons answering a question; none on an answer, which closes with ×. */
	acts?: StripAct[];
	busy?: boolean;
}

export const strips: Record<number, Strip | undefined> = $state({});

/** Hang a line under pane `pane`'s toolbar, replacing any there; undefined takes it down. */
export function setStrip(pane: number, strip: Strip | undefined): void {
	strips[pane] = strip;
}
