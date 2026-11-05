<script lang="ts">
	// One page drawn small, once it comes into view: a document may have hundreds, and the pages editor shows them all.
	import type { PDFDocumentProxy } from 'pdfjs-dist';

	let { doc, index, turn = 0, width = 112 }: { doc: PDFDocumentProxy; index: number; turn?: number; width?: number } = $props();

	let canvas = $state<HTMLCanvasElement | null>(null);
	let seen = $state(false);

	$effect(() => {
		if (!canvas) return;
		const watch = new IntersectionObserver(([e]) => {
			if (e.isIntersecting) seen = true;
		});
		watch.observe(canvas);
		return () => watch.disconnect();
	});

	$effect(() => {
		if (!seen || !canvas) return;
		const c = canvas;
		let dropped = false;
		let task: { cancel(): void; promise: Promise<unknown> } | null = null;
		void doc.getPage(index + 1).then((page) => {
			if (dropped) return;
			const rotation = (page.rotate + turn + 360) % 360;
			const base = page.getViewport({ scale: 1, rotation });
			const view = page.getViewport({ scale: (width * 2) / base.width, rotation });
			c.width = Math.floor(view.width);
			c.height = Math.floor(view.height);
			const ctx = c.getContext('2d');
			if (!ctx) return;
			task = page.render({ canvasContext: ctx, viewport: view, canvas: c }) as unknown as typeof task;
			task?.promise.catch(() => {});
		});
		return () => {
			dropped = true;
			task?.cancel();
		};
	});
</script>

<canvas bind:this={canvas} style="width: {width}px;"></canvas>

<style>
	canvas {
		display: block;
		min-height: 60px;
		background: #fff;
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.18);
	}
</style>
