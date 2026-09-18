import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

// arras is a single-page application served as files: locally by a publisher that serves index.html for unknown paths, or prerendered per route for a static deployment (milestone M2). The interface it renders is docs/specs in the loom-arras workspace.
//
// ARRAS_BASE is the path the app is served under, empty for the root. It is a build-time choice because SvelteKit
// resolves routes and assets against it; where the *corpus* lives is a separate, runtime choice (src/lib/paths.ts),
// so a bundle built for one path can still be pointed at a corpus served from another.
const raw = (process.env.ARRAS_BASE ?? '').replace(/\/+$/, '');
const base = (raw && !raw.startsWith('/') ? '/' + raw : raw) as '' | `/${string}`;

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
			},
			adapter: adapter({ fallback: 'index.html', strict: false }),
			paths: { base }
		})
	],
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'unit',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}', 'tests/unit/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
