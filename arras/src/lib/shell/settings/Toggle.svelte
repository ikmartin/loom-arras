<script lang="ts">
	// A setting that is on or off, as a switch: a checkbox underneath, so it is read and set as one.
	let { checked, set, label, test, disabled = false }: { checked: boolean; set: (on: boolean) => void; label: string; test: string; disabled?: boolean } = $props();
</script>

<input type="checkbox" role="switch" {checked} {disabled} aria-label={label} onchange={(e) => set(e.currentTarget.checked)} data-testid={test} />

<style>
	input {
		appearance: none;
		position: relative;
		width: 38px;
		height: 22px;
		margin: 0;
		border-radius: 11px;
		background: var(--rule-strong);
		cursor: pointer;
		flex: none;
	}
	input::after {
		content: '';
		position: absolute;
		top: 3px;
		left: 3px;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: var(--sheet);
		box-shadow: 0 1px 2px rgb(0 0 0 / 25%);
		transition: left 0.15s;
	}
	input:checked {
		background: var(--link);
	}
	input:checked::after {
		left: 19px;
	}
	input:disabled {
		opacity: 0.45;
		cursor: default;
	}
	input:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: 2px;
	}
</style>
