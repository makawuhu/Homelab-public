#!/usr/bin/env python3
"""Generate README.md sections from inventory data.

Content between <!-- gen:NAME --> ... <!-- /gen:NAME --> sentinels is replaced.
Run with --write to update README.md, or --check to verify it is current (CI use).

Generated sections:
  gen:services       — Services table (services with a healthcheck URL)
  gen:repo-structure — services/ directory listing inside Repo Structure code block
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency: pip install pyyaml")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
INVENTORY = REPO_ROOT / "inventory"
SERVICES_DIR = REPO_ROOT / "services"

# Static lines that follow the generated services/ block inside Repo Structure
_REPO_STRUCTURE_SUFFIX = """\

network/               Network configs (NPM, OPNsense, iperf3)
proxmox/               Host docs — hardware, ZFS, GPU passthrough, backups
vms/                   VM-specific docs
auth/                  Auth / SSO overview
docs/                  DR procedure, pipeline docs
scripts/               Utility scripts (inventory.sh, deploy-all.sh, sanitize-push.sh)
secrets/               SOPS-encrypted secrets (never plaintext)

.gitea/
  workflows/ci.yml     CI — conventional commit linting on every PR
  RUNNER_SETUP.md      Gitea Actions runner setup guide"""


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def auto_display_name(key):
    return " ".join(w.capitalize() for w in key.replace("-", " ").split())


def host_label(hosts, host_key):
    if host_key not in hosts:
        return "—"
    h = hosts[host_key]
    prefix = "VM" if h.get("type") == "vm" else "CT"
    return f"{prefix} {h['proxmox_id']}"


def ct_from_notes(notes):
    if not notes:
        return "—"
    m = re.search(r'\bCT\s+(\d+)', str(notes))
    return f"CT {m.group(1)}" if m else "—"


def first_clause(text):
    if not text:
        return ""
    return str(text).split(';')[0].strip()


def gen_services_table(hosts, services):
    rows = []
    for key in sorted(services.keys()):
        svc_yaml_path = SERVICES_DIR / key / "service.yaml"
        if not svc_yaml_path.exists():
            continue
        svc = load_yaml(svc_yaml_path) or {}
        healthcheck = svc.get("healthcheck")
        if not healthcheck:
            continue
        display = svc.get("display_name") or auto_display_name(key)
        host_key = services[key].get("host")
        category = services[key].get("category")
        if host_key:
            host_col = host_label(hosts, host_key)
        elif category == "ct_resident":
            notes = services[key].get("notes") or svc.get("notes", "")
            host_col = ct_from_notes(notes)
        else:
            host_col = "—"
        rows.append((display, healthcheck, host_col))

    lines = ["| Service | URL | Host |", "|---------|-----|------|"]
    for name, url, host in rows:
        lines.append(f"| {name} | {url} | {host} |")
    return "\n".join(lines)


def gen_repo_structure(services):
    col_w = max(len(k) + 3 for k in services.keys()) + 2
    col_w = max(col_w, 26)

    lines = ["```", "services/"]
    for key in sorted(services.keys()):
        svc_yaml_path = SERVICES_DIR / key / "service.yaml"
        svc_notes = ""
        inv_notes = services[key].get("notes", "")
        if svc_yaml_path.exists():
            svc = load_yaml(svc_yaml_path) or {}
            svc_notes = svc.get("notes", "")
        desc = first_clause(svc_notes) or first_clause(inv_notes)
        name_col = f"  {key}/"
        if desc:
            lines.append(f"{name_col:<{col_w}}{desc}")
        else:
            lines.append(name_col)
    lines.append(_REPO_STRUCTURE_SUFFIX)
    lines.append("```")
    return "\n".join(lines)


def replace_sentinel(content, name, body):
    open_tag = f"<!-- gen:{name} -->"
    close_tag = f"<!-- /gen:{name} -->"
    if open_tag not in content:
        raise ValueError(f"Sentinel not found in README.md: {open_tag!r}")
    pattern = re.compile(
        re.escape(open_tag) + r".*?" + re.escape(close_tag),
        re.DOTALL,
    )
    return pattern.sub(f"{open_tag}\n{body}\n{close_tag}", content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Update README.md in place")
    group.add_argument("--check", action="store_true", help="Exit non-zero if stale")
    args = parser.parse_args()

    hosts = load_yaml(INVENTORY / "hosts.yaml")
    services = load_yaml(INVENTORY / "services.yaml")

    services_table = gen_services_table(hosts, services)
    repo_structure = gen_repo_structure(services)

    current = README.read_text()
    updated = replace_sentinel(current, "services", services_table)
    updated = replace_sentinel(updated, "repo-structure", repo_structure)

    if args.write:
        if updated != current:
            README.write_text(updated)
            print("README.md updated.")
        else:
            print("README.md already up to date.")
    else:
        if updated != current:
            print("FAIL — README.md generated sections are stale.")
            print("Fix: python3 scripts/gen_docs.py --write")
            sys.exit(1)
        print("OK — README.md generated sections are current.")


if __name__ == "__main__":
    main()
