export interface LabelCandidate { id: string; x: number; y: number; width: number; priority: number; radius: number }
interface Rect { x: number; y: number; w: number; h: number }
const overlaps = (a: Rect, b: Rect) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

/** Greedy label placement in screen pixels; the graph geometry never moves to make room for text. */
export function placeLabels(candidates: LabelCandidate[], width: number, height: number) {
	const occupied: Rect[] = candidates.map((c) => ({ x: c.x - c.radius - 2, y: c.y - c.radius - 10, w: 2 * c.radius + 4, h: 2 * c.radius + 12 }));
	const result = new Map<string, { x: number; y: number }>();
	for (const c of [...candidates].sort((a, b) => a.priority - b.priority || a.id.localeCompare(b.id))) {
		for (const y of [c.y + c.radius + 4, c.y - c.radius - 28]) {
			const rect = { x: c.x - c.width / 2 - 3, y, w: c.width + 6, h: 18 };
			if (rect.x < 0 || rect.y < 0 || rect.x + rect.w > width || rect.y + rect.h > height || occupied.some((o) => overlaps(o, rect))) continue;
			occupied.push(rect);
			result.set(c.id, { x: c.x, y: y + 13 });
			break;
		}
	}
	return result;
}
