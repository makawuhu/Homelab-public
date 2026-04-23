#!/usr/bin/env python3
"""
Classify collected packages against patch-policy.yml.
Output: one classified YAML manifest per host in <run-dir>/classified/
"""
import sys
import os
import json
import re
import fnmatch
import argparse
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    sys.exit("Error: PyYAML required — run: apt-get install -y python3-yaml")


def strip_version(v):
    """Strip epoch and Debian revision, return upstream version string."""
    # Strip epoch (e.g. "1:" or "5:")
    v = re.sub(r'^\d+:', '', v)
    # Strip Debian revision (e.g. "-1ubuntu2", "-1~deb12u3")
    v = re.sub(r'[-~][^.-].*$', '', v)
    return v.strip()


def parse_version(v):
    """Parse a version string into a tuple of integers for comparison."""
    v = strip_version(v)
    parts = re.split(r'[.\-_]', v)
    result = []
    for p in parts[:4]:
        m = re.match(r'^(\d+)', p)
        result.append(int(m.group(1)) if m else 0)
    while len(result) < 4:
        result.append(0)
    return tuple(result)


def version_delta(installed, candidate):
    """
    Return 'major', 'minor', or 'patch' based on the version bump.
    """
    iv = parse_version(installed)
    cv = parse_version(candidate)
    if cv[0] != iv[0]:
        return 'major'
    if cv[1] != iv[1]:
        return 'minor'
    return 'patch'


CONSTRAINT_LEVELS = {'~patch': 0, '~minor': 1, '~major': 2}
DELTA_LEVELS = {'patch': 0, 'minor': 1, 'major': 2}


def exceeds_constraint(installed, candidate, constraint):
    """Return True if the version bump exceeds the semver_constraint."""
    delta = version_delta(installed, candidate)
    return DELTA_LEVELS[delta] > CONSTRAINT_LEVELS.get(constraint, 2)


def match_rule(pkg_name, rules):
    """Return the first matching rule for a package name, or None."""
    for rule in rules:
        pattern = rule.get('match', '')
        if fnmatch.fnmatch(pkg_name, pattern):
            return rule
    return None


def classify_package(pkg, host_name, policy):
    """
    Classify a single package. Returns dict with action, rule_matched, reason, version_delta.
    """
    name = pkg['name']
    installed = pkg.get('installed', '0')
    candidate = pkg.get('candidate', '0')

    # Check host overrides first
    host_rules = policy.get('host_overrides', {}).get(host_name, [])
    rule = match_rule(name, host_rules)

    # Fall through to global rules
    if rule is None:
        rule = match_rule(name, policy.get('rules', []))

    # Use default if no rule matched
    if rule is None:
        action = policy.get('default_action', 'needs-review')
        reason = 'No matching rule — using default_action'
        rule_matched = '<default>'
        constraint = None
    else:
        action = rule.get('action', 'needs-review')
        reason = rule.get('reason', '')
        rule_matched = rule.get('match', '')
        constraint = rule.get('semver_constraint')

    delta = version_delta(installed, candidate)

    # If auto but version bump exceeds constraint, escalate to needs-review
    if action == 'auto' and constraint and exceeds_constraint(installed, candidate, constraint):
        action = 'needs-review'
        reason = (reason + f' (escalated: {delta} bump exceeds {constraint})').strip()

    return {
        'name': name,
        'installed': installed,
        'candidate': candidate,
        'arch': pkg.get('arch', 'amd64'),
        'action': action,
        'rule_matched': rule_matched,
        'reason': reason,
        'version_delta': delta,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--policy', required=True)
    args = parser.parse_args()

    with open(args.policy) as f:
        policy = yaml.safe_load(f)

    raw_dir = os.path.join(args.run_dir, 'raw')
    classified_dir = os.path.join(args.run_dir, 'classified')
    os.makedirs(classified_dir, exist_ok=True)

    for fname in sorted(os.listdir(raw_dir)):
        if not fname.endswith('.json'):
            continue

        with open(os.path.join(raw_dir, fname)) as f:
            data = json.load(f)

        host = data['host']
        status = data.get('status', 'ok')

        auto = []
        needs_review = []

        if status == 'ok' and data.get('packages'):
            for pkg in data['packages']:
                result = classify_package(pkg, host, policy)
                if result['action'] == 'auto':
                    auto.append(result)
                else:
                    needs_review.append(result)

        manifest = {
            'host': host,
            'ip': data['ip'],
            'run_id': os.path.basename(args.run_dir),
            'status': status,
            'classified_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'auto': auto,
            'needs_review': needs_review,
        }

        out_path = os.path.join(classified_dir, f'{host}.yml')
        with open(out_path, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

        auto_count = len(auto)
        review_count = len(needs_review)
        print(f"  {host}: {auto_count} auto, {review_count} needs-review ({status})")


if __name__ == '__main__':
    main()
