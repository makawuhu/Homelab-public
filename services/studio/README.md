# Studio

Creative workspace UI for the image generation pipeline.

- **Host:** CT 132 (`192.168.x.168`)
- **Port:** 3000
- **External URL:** https://studio.yourdomain.com
- **Stack:** Svelte + Vite, served via nginx in Docker

## What it does

Single-page app that submits SD image generation jobs to the GPU API (gpu.yourdomain.com), polls for completion, and displays the result. Designed to grow into a full pipeline workspace (image → STL → 3MF).

## Deployment

```bash
./deploy.sh
```

Builds `studio:local` on CT 132 via rsync + `docker build`, then starts the container. Re-run on any source change.

## Architecture

```
Browser → https://studio.yourdomain.com (NPM proxy ID 84, wildcard cert)
       → CT 132 :3000 (nginx serving Svelte dist)
       → https://gpu.yourdomain.com/jobs (job submission + polling)
       → https://gpu-outputs.yourdomain.com/{filename} (result image)
```

## Source layout

```
app/
  src/
    App.svelte        Main UI — controls panel + canvas
    lib/api.js        GPU API client (submit, poll, outputUrl)
  index.html
  package.json
  vite.config.js
Dockerfile            Multi-stage: node:20-alpine build → nginx:alpine serve
nginx.conf            SPA fallback (try_files → index.html)
compose.yml           Port 3000:80, restart unless-stopped
deploy.sh             rsync + build + up on CT 132
```

## Environment

No env vars required — API URLs are hardcoded in `src/lib/api.js`:
- `GPU_API` = `https://gpu.yourdomain.com`
- `OUTPUTS_BASE` = `https://gpu-outputs.yourdomain.com`

To change the model or defaults, edit `src/lib/api.js` and redeploy.

## CORS

The GPU API has `CORSMiddleware` with `allow_origins=["*"]`. If Studio ever moves to a different domain, no changes needed on the API side.
