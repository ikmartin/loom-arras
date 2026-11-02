<script lang="ts">
	// What Docs shows of the project in this browser.
	import { prefs } from '$lib/prefs.svelte';
	import Row from './Row.svelte';
	import Toggle from './Toggle.svelte';
</script>

<div class="card">
	<Row id="hide-aux"><Toggle label="Hide aux LaTeX files" test="hide-aux" checked={prefs.hideAux} set={(on) => (prefs.hideAux = on)} /></Row>
	<Row id="hide-agent-docs"><Toggle label="Hide agent documents" test="hide-agent-docs" checked={prefs.hideAgentDocs} set={(on) => (prefs.hideAgentDocs = on)} /></Row>
</div>
