// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
	namespace svelteHTML {
		interface IntrinsicElements {
			'ninja-keys': { placeholder?: string; [key: string]: unknown };
		}
	}
}

export {};
