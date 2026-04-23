<script>
  import { generateImage, pollJob, outputUrl, fetchModels } from './lib/api.js'
  import { loadPresets, savePreset, deletePreset } from './lib/presets.js'
  import { onMount } from 'svelte'

  let prompt = ''
  let negativePrompt = ''
  let steps = 30
  let width = 1024
  let height = 1024
  let seed = ''
  let guidanceScale = 7.5

  // Models
  let models = []
  let selectedModel = ''
  onMount(async () => {
    try {
      models = await fetchModels()
      if (models.length) selectedModel = models[0].container_path
    } catch {}
  })

  let status = 'idle'   // idle | generating | done | error
  let statusText = ''
  let imageUrl = null

  const SIZES = ['512x512', '512x768', '768x512', '768x768', '1024x1024']
  let selectedSize = '1024x1024'
  $: {
    const [w, h] = selectedSize.split('x').map(Number)
    width = w
    height = h
  }

  // Presets
  let presets = loadPresets()
  let selectedPreset = ''
  let newPresetName = ''
  let showSaveInput = false

  function applyPreset(name) {
    const p = presets.find(p => p.name === name)
    if (!p) return
    prompt = p.prompt ?? prompt
    negativePrompt = p.negativePrompt ?? negativePrompt
    steps = p.steps ?? steps
    selectedSize = p.selectedSize ?? selectedSize
    seed = p.seed ?? seed
    guidanceScale = p.guidanceScale ?? guidanceScale
    selectedPreset = name
  }

  function handleSavePreset() {
    const name = newPresetName.trim()
    if (!name) return
    presets = savePreset(name, { prompt, negativePrompt, steps, selectedSize, seed, guidanceScale })
    selectedPreset = name
    newPresetName = ''
    showSaveInput = false
  }

  function handleDeletePreset() {
    if (!selectedPreset) return
    presets = deletePreset(selectedPreset)
    selectedPreset = ''
  }

  async function submit() {
    if (!prompt.trim()) return
    status = 'generating'
    statusText = 'Submitting job...'
    imageUrl = null

    try {
      const jobId = await generateImage({ prompt, negativePrompt, steps, width, height, seed: seed || null, guidanceScale, modelPath: selectedModel })
      statusText = 'Waiting in queue...'

      while (true) {
        await new Promise(r => setTimeout(r, 3000))
        const job = await pollJob(jobId)

        if (job.status === 'completed') {
          const filename = job.result.stdout.trim()
          imageUrl = outputUrl(filename)
          status = 'done'
          statusText = ''
          break
        } else if (job.status === 'failed') {
          throw new Error(job.result?.stderr?.slice(0, 200) || job.error || 'Job failed')
        } else if (job.status === 'running') {
          statusText = 'Generating...'
        }
      }
    } catch (e) {
      status = 'error'
      statusText = e.message
    }
  }

  function reset() {
    status = 'idle'
    statusText = ''
    imageUrl = null
  }
</script>

<main>
  <header>
    <h1>Studio</h1>
  </header>

  <div class="workspace">
    <aside class="controls">

      <!-- Presets -->
      <div class="section-label">Presets</div>
      <div class="preset-row">
        <select bind:value={selectedPreset} on:change={() => applyPreset(selectedPreset)} disabled={status === 'generating'}>
          <option value="">— select preset —</option>
          {#each presets as p}
            <option value={p.name}>{p.name}</option>
          {/each}
        </select>
        <button class="icon-btn danger" title="Delete preset" on:click={handleDeletePreset} disabled={!selectedPreset || status === 'generating'}>✕</button>
      </div>

      {#if showSaveInput}
        <div class="save-row">
          <input type="text" bind:value={newPresetName} placeholder="Preset name..." on:keydown={e => e.key === 'Enter' && handleSavePreset()} />
          <button class="icon-btn" on:click={handleSavePreset} disabled={!newPresetName.trim()}>Save</button>
          <button class="icon-btn" on:click={() => { showSaveInput = false; newPresetName = '' }}>Cancel</button>
        </div>
      {:else}
        <button class="text-btn" on:click={() => showSaveInput = true} disabled={status === 'generating'}>
          + Save current as preset
        </button>
      {/if}

      <div class="divider" />

      <!-- Model -->
      <label>
        Model
        <select bind:value={selectedModel} disabled={status === 'generating'}>
          {#if models.length === 0}
            <option value="">Loading models...</option>
          {:else}
            {#each models as m}
              <option value={m.container_path}>{m.name} ({m.size_gb}GB{m.is_xl ? ' · XL' : ''})</option>
            {/each}
          {/if}
        </select>
      </label>

      <!-- Prompt -->
      <label>
        Prompt
        <textarea bind:value={prompt} rows="4" placeholder="Describe your image..." disabled={status === 'generating'} />
      </label>

      <label>
        Negative prompt
        <textarea bind:value={negativePrompt} rows="2" placeholder="What to avoid..." disabled={status === 'generating'} />
      </label>

      <div class="row">
        <label>
          Size
          <select bind:value={selectedSize} disabled={status === 'generating'}>
            {#each SIZES as s}
              <option value={s}>{s}</option>
            {/each}
          </select>
        </label>

        <label>
          Steps
          <input type="number" bind:value={steps} min="1" max="150" disabled={status === 'generating'} />
        </label>
      </div>

      <div class="row">
        <label>
          Guidance
          <input type="number" bind:value={guidanceScale} min="1" max="20" step="0.5" disabled={status === 'generating'} />
        </label>

        <label>
          Seed <span class="hint">(opt.)</span>
          <input type="number" bind:value={seed} placeholder="Random" disabled={status === 'generating'} />
        </label>
      </div>

      <button class="generate" on:click={submit} disabled={status === 'generating' || !prompt.trim()}>
        {status === 'generating' ? 'Generating...' : 'Generate'}
      </button>
    </aside>

    <section class="canvas">
      {#if imageUrl}
        <div class="result">
          <img src={imageUrl} alt="Generated" />
          <div class="actions">
            <a href={imageUrl} download target="_blank">Download</a>
            <button on:click={reset}>New image</button>
          </div>
        </div>
      {:else if status === 'generating'}
        <div class="placeholder">
          <div class="spinner" />
          <p>{statusText}</p>
        </div>
      {:else if status === 'error'}
        <div class="placeholder error">
          <p>{statusText}</p>
          <button on:click={reset}>Try again</button>
        </div>
      {:else}
        <div class="placeholder">
          <p>Enter a prompt and click Generate</p>
        </div>
      {/if}
    </section>
  </div>
</main>

<style>
  :global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) { background: #0f0f0f; color: #e0e0e0; font-family: system-ui, sans-serif; height: 100vh; }

  main { display: flex; flex-direction: column; height: 100vh; }

  header {
    padding: 12px 20px;
    border-bottom: 1px solid #222;
    background: #141414;
  }
  header h1 { font-size: 1rem; font-weight: 600; color: #fff; letter-spacing: 0.05em; }

  .workspace { display: flex; flex: 1; overflow: hidden; }

  aside.controls {
    width: 280px;
    flex-shrink: 0;
    padding: 16px;
    border-right: 1px solid #222;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow-y: auto;
    background: #121212;
  }

  .section-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #555; }

  .preset-row { display: flex; gap: 6px; }
  .preset-row select { flex: 1; }

  .save-row { display: flex; gap: 6px; }
  .save-row input { flex: 1; }

  .divider { height: 1px; background: #222; margin: 2px 0; }

  label { display: flex; flex-direction: column; gap: 5px; font-size: 0.8rem; color: #999; }
  .hint { color: #555; font-size: 0.75rem; }

  textarea, input, select {
    background: #1e1e1e;
    border: 1px solid #2e2e2e;
    border-radius: 6px;
    color: #e0e0e0;
    font-size: 0.875rem;
    padding: 8px 10px;
    width: 100%;
    resize: vertical;
  }
  textarea:focus, input:focus, select:focus { outline: none; border-color: #555; }
  textarea:disabled, input:disabled, select:disabled { opacity: 0.5; cursor: not-allowed; }

  .row { display: flex; gap: 10px; }
  .row label { flex: 1; }

  .icon-btn {
    background: #1e1e1e;
    border: 1px solid #2e2e2e;
    border-radius: 6px;
    color: #ccc;
    font-size: 0.8rem;
    padding: 6px 10px;
    cursor: pointer;
    white-space: nowrap;
  }
  .icon-btn:hover:not(:disabled) { border-color: #555; color: #fff; }
  .icon-btn.danger:hover:not(:disabled) { border-color: #e05555; color: #e05555; }
  .icon-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .text-btn {
    background: none;
    border: none;
    color: #6c63ff;
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0;
    text-align: left;
  }
  .text-btn:hover:not(:disabled) { color: #9d97ff; }
  .text-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  button.generate {
    background: #6c63ff;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 10px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
    margin-top: 4px;
  }
  button.generate:hover:not(:disabled) { background: #7c74ff; }
  button.generate:disabled { opacity: 0.5; cursor: not-allowed; }

  section.canvas {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    overflow: auto;
  }

  .placeholder {
    text-align: center;
    color: #444;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .placeholder.error { color: #e05555; }
  .placeholder p { font-size: 0.9rem; }

  .spinner {
    width: 36px; height: 36px;
    border: 3px solid #333;
    border-top-color: #6c63ff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .result { display: flex; flex-direction: column; align-items: center; gap: 14px; }
  .result img { max-width: 100%; max-height: calc(100vh - 160px); border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.5); }

  .actions { display: flex; gap: 10px; }
  .actions a, .actions button {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 6px;
    color: #ccc;
    font-size: 0.85rem;
    padding: 7px 16px;
    cursor: pointer;
    text-decoration: none;
  }
  .actions a:hover, .actions button:hover { border-color: #555; color: #fff; }
</style>
