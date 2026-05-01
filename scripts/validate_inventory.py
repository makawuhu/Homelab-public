#!/usr/bin/env python3
"""Validate inventory/hosts.yaml, inventory/services.yaml, and services/*/service.yaml.

Checks performed:
  1. JSON schema conformance for every host and service entry
  2. service.host references a key that exists in hosts.yaml
  3. compose_managed/special require a host field
  4. Exact key-parity with git-tracked services/ directories
  5. category truth against on-disk .deploy and compose.yml presence:
       compose_managed  => .deploy present AND compose.yml/yaml present
       special          => .deploy present AND no compose file
       ct_resident      => no .deploy
       doc_only         => no .deploy
  6. host IP resolves to the same value as .deploy HOST=
  7. build: true <-> BUILD=true in .deploy (bidirectional)
  8. Duplicate top-level keys in both YAML files are rejected
  9. services/*/service.yaml validated against service_file.schema.json when present
 10. service.yaml compose_path file must exist on disk when deployable: true
 11. .deploy content: HOST key present, no unknown keys, BUILD=true requires SOURCE_PATH
 12. README.md generated sections (gen:services, gen:repo-structure) are up to date
 13. No stale .yourdomain.com URLs in .md files (must be a healthcheck in inventory or known infra)

Usage:
    python3 scripts/validate_inventory.py

Dependencies:
    pip install pyyaml jsonschema
"""

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
    import jsonschema
except ImportError as exc:
    print(f"Missing dependency: {exc}")
    print("Install with: pip install pyyaml jsonschema")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "inventory"
SCHEMAS = INVENTORY / "schemas"
SERVICES_DIR = REPO_ROOT / "services"

CATEGORIES_REQUIRING_HOST = {"compose_managed", "special"}

# All keys recognised by webhook-handler.sh
DEPLOY_ALLOWED_KEYS = {
    "HOST",         # required — target host IP
    "SSH_USER",     # optional — SSH login user (default: root)
    "REPO",         # optional — remote repo path (default: /opt/homelab)
    "BUILD",        # optional — set to "true" to build from source
    "SOURCE_PATH",  # optional — path to source checkout on remote (required when BUILD=true)
    "COMPOSE_FILE", # optional — compose filename in REPO dir (default: compose.yml)
    "GITEA_REPO",   # optional — Gitea repo path for BUILD=true source clone
    "GITHUB_REPO",  # optional — GitHub repo URL for BUILD=true source clone
}


# ---------------------------------------------------------------------------
# YAML loader that rejects duplicate top-level (and nested) mapping keys
# ---------------------------------------------------------------------------

class _DuplicateKeyLoader(yaml.SafeLoader):
    pass


def _no_duplicate_mapping(loader, node):
    loader.flatten_mapping(node)
    pairs = loader.construct_pairs(node)
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise yaml.YAMLError(f"Duplicate key: {key!r}")
        seen.add(key)
    return dict(pairs)


_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _no_duplicate_mapping,
)


def load_yaml(path):
    with open(path) as f:
        try:
            return yaml.load(f, Loader=_DuplicateKeyLoader)
        except yaml.YAMLError as exc:
            print(f"YAML ERROR in {path.relative_to(REPO_ROOT)}: {exc}")
            sys.exit(1)


def load_json(path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# On-disk helpers
# ---------------------------------------------------------------------------

def parse_deploy(service_dir):
    """Return .deploy key=value pairs as a dict, or None if the file is absent."""
    path = service_dir / ".deploy"
    if not path.exists():
        return None
    data = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                data[key.strip()] = val.strip()
    return data


def has_compose(service_dir):
    return (
        (service_dir / "compose.yml").exists()
        or (service_dir / "compose.yaml").exists()
    )


# ---------------------------------------------------------------------------
# Schema validation helper
# ---------------------------------------------------------------------------

def schema_errors(key, data, schema):
    v = jsonschema.Draft7Validator(schema)
    out = []
    for e in sorted(v.iter_errors(data), key=lambda e: str(e.path)):
        path = ".".join(str(p) for p in e.absolute_path) or "(root)"
        out.append(f"{key}: {path}: {e.message}")
    return out


# ---------------------------------------------------------------------------
# Git-tracked services/ directories
# ---------------------------------------------------------------------------

def git_service_dirs():
    result = subprocess.run(
        ["git", "ls-files", "services/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    dirs = set()
    for line in result.stdout.splitlines():
        parts = line.split("/")
        if len(parts) >= 2 and parts[1]:
            dirs.add(parts[1])
    return dirs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    required = {
        "hosts.yaml": INVENTORY / "hosts.yaml",
        "services.yaml": INVENTORY / "services.yaml",
        "schemas/host.schema.json": SCHEMAS / "host.schema.json",
        "schemas/service.schema.json": SCHEMAS / "service.schema.json",
    }
    absent = [name for name, path in required.items() if not path.exists()]
    if absent:
        for name in absent:
            print(f"MISSING: inventory/{name}")
        return 1

    hosts = load_yaml(INVENTORY / "hosts.yaml")
    services = load_yaml(INVENTORY / "services.yaml")
    host_schema = load_json(SCHEMAS / "host.schema.json")
    service_schema = load_json(SCHEMAS / "service.schema.json")

    errors = []
    known_hosts = set(hosts.keys())

    # 1+2+3 — schema conformance, host-key existence, required host field
    for key, val in hosts.items():
        errors.extend(schema_errors(f"hosts[{key}]", val, host_schema))

    for key, val in services.items():
        errors.extend(schema_errors(f"services[{key}]", val, service_schema))
        category = val.get("category")
        host_ref = val.get("host")
        if category in CATEGORIES_REQUIRING_HOST and not host_ref:
            errors.append(
                f"services[{key}]: category '{category}' requires a host field"
            )
        if host_ref and host_ref not in known_hosts:
            errors.append(
                f"services[{key}].host: '{host_ref}' not defined in hosts.yaml"
            )

    # 4 — inventory keys must exactly match git-tracked services/ directories
    real_dirs = git_service_dirs()
    inventory_keys = set(services.keys())
    for phantom in sorted(inventory_keys - real_dirs):
        errors.append(
            f"services[{phantom}]: in inventory but not a git-tracked services/ directory"
        )
    for missing_svc in sorted(real_dirs - inventory_keys):
        errors.append(
            f"services/{missing_svc}/: git-tracked directory missing from inventory"
        )

    # 5+6+7 — category, host IP, build truthfulness against on-disk files
    for key, val in services.items():
        svc_dir = SERVICES_DIR / key
        category = val.get("category")
        host_ref = val.get("host")
        deploy = parse_deploy(svc_dir)
        compose = has_compose(svc_dir)

        # category vs .deploy / compose presence
        if category == "compose_managed":
            if deploy is None:
                errors.append(f"services[{key}]: compose_managed but .deploy is absent")
            if not compose:
                errors.append(f"services[{key}]: compose_managed but no compose.yml/yaml")
        elif category == "special":
            if deploy is None:
                errors.append(f"services[{key}]: special but .deploy is absent")
            if compose:
                errors.append(
                    f"services[{key}]: special but compose.yml/yaml is present"
                    " (special means no compose file)"
                )
        elif category in ("ct_resident", "doc_only"):
            if deploy is not None:
                errors.append(
                    f"services[{key}]: {category} but .deploy is present"
                )

        # host key -> IP must match .deploy HOST=
        if host_ref and host_ref in known_hosts and deploy is not None:
            deploy_ip = deploy.get("HOST")
            host_ip = hosts[host_ref]["ip"]
            if deploy_ip != host_ip:
                errors.append(
                    f"services[{key}].host '{host_ref}' resolves to {host_ip}"
                    f" but .deploy HOST={deploy_ip!r}"
                )

        # build: true <-> BUILD=true in .deploy (bidirectional)
        inventory_build = val.get("build", False)
        deploy_build = deploy is not None and deploy.get("BUILD") == "true"
        if inventory_build and not deploy_build:
            errors.append(
                f"services[{key}]: inventory has build: true"
                " but .deploy has no BUILD=true"
            )
        if deploy_build and not inventory_build:
            errors.append(
                f"services[{key}]: .deploy has BUILD=true"
                " but inventory is missing build: true"
            )

        # 11 — .deploy content: HOST required, no unknown keys, BUILD=true → SOURCE_PATH
        if deploy is not None:
            if "HOST" not in deploy:
                errors.append(f"services/{key}/.deploy: HOST key is missing")
            for uk in sorted(set(deploy.keys()) - DEPLOY_ALLOWED_KEYS):
                errors.append(f"services/{key}/.deploy: unknown key '{uk}'")
            if deploy.get("BUILD") == "true" and not deploy.get("SOURCE_PATH"):
                errors.append(
                    f"services/{key}/.deploy: BUILD=true requires SOURCE_PATH"
                )

    # 9+10 — validate services/*/service.yaml against service_file.schema.json
    service_file_schema_path = SCHEMAS / "service_file.schema.json"
    if service_file_schema_path.exists():
        service_file_schema = load_json(service_file_schema_path)
        service_yaml_count = 0
        for svc_name in sorted(services.keys()):
            svc_yaml = SERVICES_DIR / svc_name / "service.yaml"
            if not svc_yaml.exists():
                continue
            service_yaml_count += 1
            svc_data = load_yaml(svc_yaml)
            if svc_data is None:
                errors.append(f"services/{svc_name}/service.yaml: empty file")
                continue
            errors.extend(
                schema_errors(f"services/{svc_name}/service.yaml", svc_data, service_file_schema)
            )
            # compose_path must exist on disk when deployable: true
            if svc_data.get("deployable") and "compose_path" in svc_data:
                cp = SERVICES_DIR / svc_name / svc_data["compose_path"]
                if not cp.exists():
                    errors.append(
                        f"services/{svc_name}/service.yaml: compose_path"
                        f" '{svc_data['compose_path']}' not found on disk"
                    )
    else:
        service_yaml_count = 0

    # 13 — no stale .yourdomain.com URLs in .md files
    # Collect all healthcheck URLs from service.yaml files
    known_urls = set()
    for svc_name in services:
        svc_yaml = SERVICES_DIR / svc_name / "service.yaml"
        if svc_yaml.exists():
            svc_data = load_yaml(svc_yaml)
            if svc_data and svc_data.get("healthcheck"):
                known_urls.add(svc_data["healthcheck"].rstrip("/"))
    # Infrastructure UIs / companion endpoints not tracked as separate services
    known_urls |= {
        "http://nginx.yourdomain.com",
        "http://proxmox.yourdomain.com",
        "https://gpu-outputs.yourdomain.com",  # outputs viewer endpoint of the gpu service
    }
    url_pattern = re.compile(r'https?://[a-z0-9._-]+\.yourhostname\.com\b')
    # Strip generated sentinel blocks before scanning (they're always current)
    sentinel_pattern = re.compile(r'<!--\s*gen:[^>]+-->.*?<!--\s*/gen:[^>]+-->', re.DOTALL)
    for md_file in sorted(REPO_ROOT.rglob("*.md")):
        try:
            content = sentinel_pattern.sub("", md_file.read_text())
        except Exception:
            continue
        for url in url_pattern.findall(content):
            url = url.rstrip("/")
            if url not in known_urls:
                rel = md_file.relative_to(REPO_ROOT)
                errors.append(
                    f"{rel}: stale URL '{url}' — not a healthcheck in any service.yaml"
                    " (add to service.yaml or remove from doc)"
                )

    # 12 — README.md generated sections must be up to date
    gen_docs = REPO_ROOT / "scripts" / "gen_docs.py"
    if gen_docs.exists():
        import subprocess
        result = subprocess.run(
            [sys.executable, str(gen_docs), "--check"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            errors.append(
                "README.md generated sections are stale"
                " — run: python3 scripts/gen_docs.py --write"
            )

    if errors:
        print(f"FAIL — {len(errors)} error(s):\n")
        for e in errors:
            print(f"  {e}")
        return 1

    svc_yaml_note = f", {service_yaml_count} service.yaml files" if service_yaml_count else ""
    print(f"OK — {len(hosts)} hosts, {len(services)} services validated{svc_yaml_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
