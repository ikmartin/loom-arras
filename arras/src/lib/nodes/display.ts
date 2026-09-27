import type { Manifest } from '$lib/manifest/types';

/** One readable identity, with numbering only in an explicitly selected document. */
export function displayNode(m: Manifest, key: string, master = '') {
	const owner = m.keys[key]?.node ?? key;
	const node = m.nodes[key] ?? m.nodes[owner];
	if (!node) return { name: key, context: '', id: key, accessible: key };
	const number = master ? node.numbers[master]?.number : '';
	const kind = [node.taxon, number].filter(Boolean).join(' ');
	let name = node.name?.trim() || node.title?.trim() || (number ? kind : key);
	if (key !== owner && !m.nodes[key]) {
		const index = m.nodes[owner]?.proofs.indexOf(key) ?? -1;
		name = `Proof${index > 0 ? ` ${index + 1}` : ''} of ${node.name?.trim() || node.title?.trim() || kind || owner}`;
	}
	const section = master ? m.nodes[node.parent[master]] : undefined;
	const context = [name === kind ? '' : kind, section?.name || section?.title].filter(Boolean).join(' · ');
	return { name, context, id: key, accessible: [...new Set([name, context, key].filter(Boolean))].join(' · ') };
}
