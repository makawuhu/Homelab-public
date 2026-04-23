const GPU_API = 'https://gpu.yourdomain.com'
const OUTPUTS_BASE = 'https://gpu-outputs.yourdomain.com'

export async function fetchModels() {
  const res = await fetch(`${GPU_API}/models`)
  if (!res.ok) throw new Error(`Failed to fetch models: ${res.status}`)
  const { models } = await res.json()
  return models
}

export async function generateImage({ prompt, negativePrompt, steps, width, height, seed, guidanceScale = 7.5, modelPath }) {
  const payload = {
    job_type: 'custom_docker',
    timeout_seconds: 180,
    payload: {
      image: 'sd-job:local',
      env: {
        PROMPT: prompt,
        ...(negativePrompt && { NEGATIVE_PROMPT: negativePrompt }),
        STEPS: String(steps),
        WIDTH: String(width),
        HEIGHT: String(height),
        GUIDANCE_SCALE: String(guidanceScale),
        MODEL_PATH: modelPath || '/models/juggernaut-xl-v9.safetensors',
        ...(seed && { SEED: String(seed) }),
      },
      volumes: {
        '/opt/models': '/models',
        '/opt/outputs': '/output',
      },
      shm_size: '2g',
    },
  }

  const res = await fetch(`${GPU_API}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`)
  const { job_id } = await res.json()
  return job_id
}

export async function pollJob(jobId) {
  const res = await fetch(`${GPU_API}/jobs/${jobId}`)
  if (!res.ok) throw new Error(`Poll failed: ${res.status}`)
  return res.json()
}

export function outputUrl(filename) {
  return `${OUTPUTS_BASE}/${filename}`
}
