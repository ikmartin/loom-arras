// The force layout's simulation off the page's thread: 320 steps over a few hundred nodes is a third of a second the reader would otherwise wait through with the page frozen.

import { forcePositions, type ForceInput } from './force-sim';

self.onmessage = (e: MessageEvent<ForceInput & { n: number }>) => {
	self.postMessage({ n: e.data.n, out: forcePositions(e.data) });
};
