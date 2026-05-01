# ollama-gpu

GPU-accelerated Ollama on VM 134 (`ai`, `192.168.x.170`). RTX A2000 12GB, local models only.

- **Port:** 11434
- **Internal URL:** http://192.168.x.170:11434 (no NPM proxy — LAN access only)
- **Models stored at:** `/opt/ollama` on VM 134

## Pull a model

```bash
curl http://192.168.x.170:11434/api/pull -d '{"name":"llama3.2"}'
```

## Run inference

```bash
curl http://192.168.x.170:11434/api/generate \
  -d '{"model":"llama3.2","prompt":"Hello","stream":false}'
```
