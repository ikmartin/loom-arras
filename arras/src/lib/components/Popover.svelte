<script lang="ts">
	// One floating surface (plan 0.13.3): a control that opens a box beside itself, or a modal dialog over the page. Both close on a press outside the box or on Escape through `dismiss` (DR-121), and appear and go without animation.
	//
	// The anchored box is `position: fixed`, placed from its control's rectangle, so a box opened from inside a column that clips its overflow (the side panel, the icon strip) is not cut to that column. A box hung from a control is otherwise sized by the control's containing block, which in the 44px strip is nothing.
	import type { Snippet } from 'svelte';
	import { dismiss } from '$lib/dismiss';
	import { portal } from '$lib/portal';

	type Props = {
		/** Whether the box is showing; bind it to open or close from outside. */
		open?: boolean;
		/** The control that opens the box, given its state and a toggle. Omitted for a modal, which something else opens. */
		trigger?: Snippet<[{ open: boolean; toggle: () => void }]>;
		children: Snippet;
		/** Where the box stands relative to its control. */
		placement?: 'above' | 'below' | 'right';
		/** Which edge of the control the box lines up with. */
		align?: 'start' | 'end';
		/** The box's width in px; default its content's. */
		width?: number;
		/** A dialog over a backdrop rather than a box beside a control. */
		modal?: boolean;
		/** The anchor takes the full width of its container rather than its control's. */
		block?: boolean;
		role?: string;
		label?: string;
		testid?: string;
		onclose?: () => void;
	};

	let { open = $bindable(false), trigger, children, placement = 'below', align = 'start', width, modal = false, block = false, role, label, testid, onclose }: Props = $props();

	let anchor = $state<HTMLElement | null>(null);
	let place = $state('');

	function close(): void {
		if (!open) return;
		open = false;
		onclose?.();
	}

	function toggle(): void {
		if (open) close();
		else open = true;
	}

	/** Place the box against its control, inside the window. Re-run on resize and on any scroll, since a fixed box does not travel with a control that moves. */
	function measure(): void {
		const at = (anchor?.firstElementChild ?? anchor)?.getBoundingClientRect();
		if (!at) return;
		const gap = 4;
		const vw = window.innerWidth;
		const vh = window.innerHeight;
		const s: string[] = [];
		if (placement === 'right') {
			s.push(`left: ${at.right + gap}px`, `top: ${Math.max(gap, at.top)}px`, `max-height: ${vh - Math.max(gap, at.top) - gap}px`);
		} else {
			if (placement === 'above') s.push(`bottom: ${vh - at.top + gap}px`, `max-height: ${at.top - 2 * gap}px`);
			else s.push(`top: ${at.bottom + gap}px`, `max-height: ${vh - at.bottom - 2 * gap}px`);
			if (align === 'end') s.push(`right: ${Math.max(gap, vw - at.right)}px`);
			else s.push(`left: ${Math.max(gap, Math.min(at.left, vw - (width ?? 0) - gap))}px`);
		}
		if (width) s.push(`width: ${width}px`);
		place = s.join('; ');
	}

	$effect(() => {
		if (modal || !open) return;
		measure();
		window.addEventListener('resize', measure);
		window.addEventListener('scroll', measure, true);
		return () => {
			window.removeEventListener('resize', measure);
			window.removeEventListener('scroll', measure, true);
		};
	});
</script>

{#if modal}
	{#if open}
		<div class="backdrop" use:portal>
			<div class="box modal" role={role ?? 'dialog'} aria-modal="true" aria-label={label} data-testid={testid} use:dismiss={close}>
				{@render children()}
			</div>
		</div>
	{/if}
{:else}
	<span class="anchor" class:block bind:this={anchor} use:dismiss={close}>
		{#if trigger}{@render trigger({ open, toggle })}{/if}
		{#if open}
			<div class="box floating" style={place} {role} aria-label={label} data-testid={testid}>
				{@render children()}
			</div>
		{/if}
	</span>
{/if}

<style>
	.anchor {
		display: inline-block;
	}
	.anchor.block {
		display: block;
	}
	.box {
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		text-align: left;
	}
	.floating {
		position: fixed;
		z-index: 40;
		overflow-y: auto;
		max-width: min(92vw, 420px);
		box-shadow: 0 6px 20px rgb(0 0 0 / 12%);
	}
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 55;
		background: rgb(0 0 0 / 22%);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--gap);
	}
	.modal {
		max-width: 100%;
		max-height: 100%;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		box-shadow: 0 10px 40px rgb(0 0 0 / 20%);
	}
</style>
