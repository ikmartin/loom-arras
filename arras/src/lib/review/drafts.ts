// What a person is writing in an annotation's box (VerbRow): kept apart from the box, which a document re-draws whenever a new manifest arrives, so that a reply half written survives the box being made again -- its text, which verb it answers, and whether the cursor was in it. Kept for the visit, in memory; cleared when it is sent or cancelled.

export type Verb = 'reply' | 'edit' | 'discard';

export interface Draft {
	verb: Verb;
	text: string;
	severity: string;
	/** Whether the form stands open. A form closed by a press elsewhere keeps its text for when it is opened again. */
	open: boolean;
	/** Whether the cursor was in the text, and where, so a box made again takes it back. */
	focused: boolean;
	caret: number;
}

/** Drafts by annotation id. */
export const drafts = new Map<string, Draft>();
