# Failure Test Plan — Deploy Runner Phase 1

## Purpose

Validate that the runner correctly handles failures before going active.
We must prove the exception path works, not just the happy path.

## Test 1: Bad image tag

1. Modify dozzle compose.yml to use a nonexistent image tag: `amir20/dozzle:nonexistent`
2. Commit and push
3. Trigger runner
4. **Expected:** Runner reports failure, does NOT retry, does NOT rollback (shadow mode)

## Test 2: Health check failure

1. Modify dozzle health check to point at wrong port: `curl -sf http://localhost:9999/`
2. Trigger runner
3. **Expected:** Deploy succeeds but health check fails, runner reports failure

## Test 3: Missing config file

1. Trigger runner with non-existent service name
2. **Expected:** Runner exits with clear error about missing config

## Test 4: No revision change

1. Run the runner twice with no new commits
2. **Expected:** Second run detects no change and exits early

## Test 5: Rollback (active mode only)

1. Deploy a known-good version
2. Record the revision
3. Deploy a broken version
4. **Expected:** Health check fails, runner rolls back to previous revision (since rollback_allowed: true)
5. Verify service is healthy again

## Success Criteria

- All 5 tests produce expected behavior
- Result JSON files are written correctly
- Heartbeat file is touched on each run
- No orphan processes after failure
- Logs are readable in journald