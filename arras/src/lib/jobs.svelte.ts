// The library runs the publisher keeps (plan 0.24.1): a run started here answers at once with its job, and the viewer asks how each is going, once a second while any is queued or running and not at all otherwise. A run that finishes refreshes the manifest, so what it made shows.

import { store } from '$lib/manifest/client.svelte';
import { read, write, type WriteResult } from '$lib/write';

export interface JobStep {
	name: string;
	state: 'waiting' | 'running' | 'done' | 'skipped';
	n: number;
	total: number;
	item: string;
}

/** What `loom library update` prints, as its JSON envelope; a group's fixes are the publisher's words. */
export interface JobReport {
	verdict: string;
	ok: boolean;
	groups: { heading: string; count: number; items: { text: string; key?: string; fixes?: string[] }[]; next?: string }[];
	notes: string[];
}

export interface Job {
	id: string;
	kind: string;
	/** The citekeys it acts on; none is every work. */
	works: string[];
	steps: JobStep[];
	state: 'queued' | 'running' | 'done' | 'failed';
	who: string;
	online: boolean;
	redo: boolean;
	submitted: string;
	started?: string;
	finished?: string;
	error?: string;
	report?: JobReport;
}

const live = (j: Job) => j.state === 'queued' || j.state === 'running';

class Jobs {
	list = $state<Job[]>([]);
	#timer: ReturnType<typeof setTimeout> | null = null;
	#asked = false;

	/** Whether a run is queued or running. */
	readonly active = $derived(this.list.some(live));

	/** Ask the publisher once, so a run started in another tab shows here too; later asks follow a live run. */
	ask(): void {
		if (this.#asked) return;
		this.#asked = true;
		void this.refresh();
	}

	async refresh(): Promise<void> {
		const got = await read<{ jobs: Job[] }>('/jobs');
		if (!got) return;
		const before = new Map(this.list.map((j) => [j.id, j.state]));
		this.list = got.jobs;
		// a run that has finished since the last ask made something: the manifest it rebuilt shows it
		const ended = got.jobs.some((j) => !live(j) && (before.get(j.id) === 'queued' || before.get(j.id) === 'running'));
		if (ended) void store.refresh();
		if (this.#timer) clearTimeout(this.#timer);
		this.#timer = this.active ? setTimeout(() => void this.refresh(), 1000) : null;
	}

	/** Start a run over `works`, every work for none; `online` is the person's allowance of the network for this run. */
	async start(works: string[], opts: { online?: boolean; redo?: boolean } = {}): Promise<WriteResult> {
		const answer = (await write('library-update', { works, online: !!opts.online, redo: !!opts.redo })) as WriteResult & { job?: Job };
		if (answer.ok && answer.job) {
			this.list = [answer.job, ...this.list.filter((j) => j.id !== answer.job!.id)];
			void this.refresh();
		}
		return answer;
	}

	/** The latest run acting on the work `citekey`, a run over every work included. */
	forWork(citekey: string): Job | undefined {
		return this.list.find((j) => !j.works.length || j.works.includes(citekey));
	}

	/** The latest run over every work. */
	forAll(): Job | undefined {
		return this.list.find((j) => !j.works.length);
	}
}

export const jobs = new Jobs();

/** Whether a job is queued or running. */
export function running(job: Job | undefined): boolean {
	return !!job && live(job);
}
