// Badge composition (book 10.3), as a pure function so it is unit-tested. Arras renders whatever labels and colours the manifest declares; unknown labels fall back to a neutral badge.
import type { ColorClass, Key, Manifest, Node } from './manifest/types';

export interface BadgePart {
	text: string;
	color: ColorClass;
}

/** `text of @3 (paper-v2)` when a key's current text is one a landmark recorded (book 17.5); nothing when it is not, which is the ordinary case and not a fault. */
export function versionLabel(key: Key | undefined): string {
	if (!key?.version) return '';
	const n = Number(key.version.step);
	return `text of @${Number.isFinite(n) ? n : key.version.step}${key.version.name ? ' (' + key.version.name + ')' : ''}`;
}

export function stateBadge(manifest: Manifest, key: Key | undefined): BadgePart[] {
	if (!key) return [];
	const labels = manifest.states.labels;
	const label = labels[key.state];
	const parts: BadgePart[] = [{ text: label?.label ?? key.state, color: label?.color ?? 'neutral' }];
	if (key.acceptance && key.acceptance.fresh === false) {
		const stale = labels['stale'];
		parts.push({ text: stale?.label ?? 'stale', color: stale?.color ?? 'warning' });
	}
	return parts;
}

export function reviewFacts(key: Key | undefined): string {
	if (!key) return '';
	const open = Object.entries(key.reviews.open).filter(([, n]) => n > 0);
	const bits: string[] = [];
	if (open.length) bits.push(open.map(([k, n]) => `${n} open ${k}${n === 1 ? '' : 's'}`).join(', '));
	else if (key.reviews.latest_current) bits.push(`reviewed clean ${shortDate(key.reviews.latest_current.date)}`);
	if (key.reviews.detached) bits.push(`${key.reviews.detached} detached`);
	return bits.join(' · ');
}

export function nodeBadge(manifest: Manifest, node: Node): BadgePart[] {
	if (node.conflict?.length) {
		const c = manifest.states.labels['conflicted'];
		return [{ text: c?.label ?? 'conflicted', color: c?.color ?? 'negative' }];
	}
	const stmt = manifest.keys[node.id];
	if (node.incomplete.length || stmt?.state === 'incomplete') {
		const inc = manifest.states.labels['incomplete'];
		return [{ text: inc?.label ?? 'incomplete', color: inc?.color ?? 'negative' }];
	}
	const parts = stateBadge(manifest, stmt).map((p) => ({ ...p, text: 'statement ' + p.text }));
	const proofs = node.proofs.map((k) => manifest.keys[k]).filter(Boolean);
	if (proofs.length) {
		const best = proofs.slice().sort((a, b) => rank(manifest, a) - rank(manifest, b))[0];
		parts.push(...stateBadge(manifest, best).map((p) => ({ ...p, text: 'proof ' + p.text })));
	}
	for (const [name, on] of Object.entries(node.derived ?? {})) {
		if (on) {
			const d = manifest.states.derived[name];
			parts.push({ text: d?.label ?? name, color: d?.color ?? 'positive' });
		}
	}
	return parts;
}

function rank(manifest: Manifest, k: Key): number {
	if (k.state === 'accepted' && k.acceptance?.fresh !== false) return 0;
	if (k.state === 'accepted') return 1;
	if (k.state === 'draft') return 2;
	return 3;
}

export function shortDate(iso: string): string {
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}
