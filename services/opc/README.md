# OPC — Options Trading Platform

Options market data and analysis tool. Source lives in a separate repo: `your-gitea-user/opc` on Gitea. Each host clones it to `/opt/opc/` and builds images locally.

- **Prod URL:** https://opc.yourdomain.com
- **Prod host:** VM 101 (`192.168.x.5`) — `main` branch
- **Sandbox URL:** http://192.168.x.45:5173
- **Sandbox host:** CT 119 (`192.168.x.45`) — `dev` branch

## Services

| Container | Port | Purpose |
|-----------|------|---------|
| `opc-market-data` | internal | Options market data provider |
| `opc-backend` | 8010 | Python API — optional Claude integration |
| `opc-frontend` | 5173→80 | React/Vite web UI |

## Auto-deploy

Push to the source repo triggers automatic rebuilds via Gitea webhooks:
- Hook 6 → VM 101 (`main` branch → prod)
- Hook 7 → CT 119 (`dev` branch → sandbox)

## Manual rebuild

```bash
ssh root@192.168.x.5 'git -C /opt/opc pull && docker compose -f /opt/homelab/services/opc/compose.yml up --build -d'
```

## Data

Backend persistent data: `/opt/opc-data/backend` on each host.

## Environment variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional — enables Claude features in the backend |
| `RISK_FREE_RATE` | Risk-free rate for options pricing (default: `0.045`) |
