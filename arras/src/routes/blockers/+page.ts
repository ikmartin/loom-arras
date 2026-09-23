// The blockers page is retired; the address is kept so old links land on the default working document in Review (book 10.2.6).
import { redirect } from '@sveltejs/kit';
import { route } from '$lib/paths';

export function load(): never {
	redirect(308, route('/review'));
}
