// The blockers page is the review table filtered to what marks a gap; the address is kept so links to it still land (book 10.2.6).
import { redirect } from '@sveltejs/kit';

export function load(): never {
	redirect(308, '/review?show=incomplete');
}
