// The blockers page is the review table filtered to what marks a gap; the address is kept so links to it still land (book 10.2.6).
import { redirect } from '@sveltejs/kit';
import { route } from '$lib/paths';

export function load(): never {
	redirect(308, route('/review') + '?show=all');
}
