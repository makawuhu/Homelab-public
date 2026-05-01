# Ollama

LLM inference engine on CT 125 (`ollama`, `192.168.x.51`). CPU-only; cloud models via Ollama Cloud identity keys.

- **Port:** 11434
- **External URL:** http://ollama.yourdomain.com
- **Identity keys:** provisioned at container start from `OLLAMA_IDENTITY_KEY_B64` / `OLLAMA_IDENTITY_PUBKEY_B64` (encrypted in `.env.sops`)
