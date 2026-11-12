// How each document's compile stands (plan 0.29.1), as the publisher's stream says it, keyed by document path. Empty where no stream runs, as on a static host: nothing there compiles.

/** How a document's last compile ended: `ok`; `errors`, a PDF made though LaTeX reported errors; `failed`, no PDF, so the one before stays. */
export interface CompileLast {
	result: 'ok' | 'errors' | 'failed';
	ended: string;
	error: string | null;
	/** The line of the log TeX stopped at: `l.12 \hlind`. */
	at: string | null;
}

export interface Compile {
	state: 'queued' | 'compiling' | 'idle';
	/** Asked for again while compiling, so it runs once more. */
	again: boolean;
	last: CompileLast | null;
}

class Compiles {
	all = $state.raw<Record<string, Compile>>({});

	/** Take what the stream said, as one JSON object; anything else is left as it was. */
	take(data: string): void {
		try {
			const got = JSON.parse(data) as unknown;
			if (got && typeof got === 'object' && !Array.isArray(got)) this.all = got as Record<string, Compile>;
		} catch {
			// a garbled event is no news
		}
	}
}

export const compiles = new Compiles();

/** What a document's compile says to a reader in a word, or '' when there is nothing to say: compiling, waiting, or how the last run went wrong. */
export function compileWord(c: Compile | undefined): string {
	if (!c) return '';
	if (c.state === 'compiling') return 'compiling';
	if (c.state === 'queued') return 'waiting to compile';
	if (c.last?.result === 'failed') return 'did not compile';
	if (c.last?.result === 'errors') return 'compiled with errors';
	return '';
}

/** The last run's error and where TeX stopped, for a title or a line under the paper. */
export function compileError(c: Compile | undefined): string {
	const l = c?.last;
	if (!l || l.result === 'ok') return '';
	return [l.error, l.at].filter(Boolean).join(' at ');
}
