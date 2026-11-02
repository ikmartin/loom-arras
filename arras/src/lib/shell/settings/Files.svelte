<script lang="ts">
	// What Docs shows of the project in this browser.
	import { prefs } from '$lib/prefs.svelte';
	import Row from './Row.svelte';
	import Toggle from './Toggle.svelte';
</script>

<div class="card">
	<Row id="hide-aux"><Toggle label="Hide aux LaTeX files" test="hide-aux" checked={prefs.hideAux} set={(on) => (prefs.hideAux = on)} /></Row>
	<Row id="hide-agent-config"><Toggle label="Hide agent config documents" test="hide-agent-config" checked={prefs.hideAgentConfig} set={(on) => (prefs.hideAgentConfig = on)} /></Row>
</div>
