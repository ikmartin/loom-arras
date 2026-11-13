// Whether this page and the loom serving it are out of step. A running `loom serve` keeps the code it started with and serves the viewer it started with; loom updated under it (`stale`) means a restart, and a page older than the viewer the server now serves means a reload. Judged on every probe of `/_api`, so a server restarted under an open tab is noticed when the stream reconnects.

import { dev, version } from '$app/environment';
import type { Capabilities } from '$lib/write';

/** What to tell the reader: restart the server, reload the page, or nothing. */
export type Step = 'restart' | 'reload' | null;

class OutOfStep {
	said = $state<Step>(null);
	/** Put away for this page; a later probe that finds another step says it again. */
	dismissed = $state<Step>(null);
}

export const outOfStep = new OutOfStep();

/**
 * What a probe's answer says this page should tell the reader.
 *
 * Parameters
 * ----------
 * caps : Capabilities or null
 *     The answer to `GET /_api`; null where no loom serves the quilt, which is never out of step.
 * own : str, default the build's version
 *     The viewer this page runs.
 * development : bool, default whether this is a development build
 *     A development server's version is its start time, never a vendored one's, so it is never told to reload.
 *
 * Returns
 * -------
 * Step
 */
export function stepFor(caps: Capabilities | null, own: string = version, development: boolean = dev): Step {
	if (!caps) return null;
	if (caps.stale) return 'restart';
	if (!development && caps.viewer && own && caps.viewer !== own) return 'reload';
	return null;
}

/** Take a probe's answer. */
export function judge(caps: Capabilities | null): void {
	outOfStep.said = stepFor(caps);
}
