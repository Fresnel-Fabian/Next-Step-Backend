# Load tests (k6)

Performance testing for the backend, covering four distinct profiles.

## Profiles

| Profile  | Pattern                              | Duration | Purpose | Where to run |
|----------|--------------------------------------|----------|---------|--------------|
| `load`   | Ramp to 50 VUs, hold                 | ~6 min   | Baseline regression at expected peak | CI on every PR (ephemeral stack) |
| `stress` | Step-ramp 100 → 800 VUs              | ~10 min  | Find breaking point | Staging only — runner too small |
| `soak`   | 40 VUs sustained                     | ~3h10m   | Memory leaks, pool exhaustion, drift | Staging, scheduled (weekly) |
| `spike`  | 5 → 500 VUs in 20s, then drop        | ~5 min   | Burst recovery (bell-schedule rush, announcements) | Staging — autoscaling matters |

## Run locally

Start the backend + Postgres first (`./start.sh`), seed test users (`uv run python seed.py`), then:

```bash
# Default load profile
k6 run loadtests/scenarios/dashboard_flow.js

# Switch profile
PROFILE=stress k6 run loadtests/scenarios/dashboard_flow.js
PROFILE=soak   k6 run loadtests/scenarios/dashboard_flow.js
PROFILE=spike  k6 run loadtests/scenarios/dashboard_flow.js

# Against a remote URL with different creds
BASE_URL=https://staging.example.com \
TEST_USER=loadtest@example.com \
TEST_PASS=secret \
PROFILE=spike \
k6 run loadtests/scenarios/dashboard_flow.js
```

## CI workflows

| Workflow | Trigger | Target | Status |
|---|---|---|---|
| [loadtest.yml](../.github/workflows/loadtest.yml) | Every PR | Ephemeral CI stack | ✅ active |
| [stress-test.yml](../.github/workflows/stress-test.yml) | `workflow_dispatch` | Staging | ⏸ stub — needs `STAGING_URL` secret |
| [soak-test.yml](../.github/workflows/soak-test.yml) | `workflow_dispatch` | Staging | ⏸ stub — needs `STAGING_URL` secret |
| [spike-test.yml](../.github/workflows/spike-test.yml) | `workflow_dispatch` | Staging | ⏸ stub — needs `STAGING_URL` secret |

### Enabling stress/soak/spike against staging

Once a staging environment exists:

1. Add repo secrets in GitHub:
   - `STAGING_URL` — e.g. `https://api-staging.next-step.app`
   - `STAGING_TEST_USER` — load test user email
   - `STAGING_TEST_PASS` — load test user password (use a dedicated account, not real teacher/admin creds)
2. Run once via the **Actions tab → workflow → "Run workflow"** to verify.
3. To schedule recurring runs, uncomment the `schedule:` block in each workflow YAML.

Recommended schedules once enabled:
- **Stress**: nightly (catches gradual capacity regressions)
- **Soak**: weekly, Saturday 01:00 UTC (off-peak)
- **Spike**: monthly, or manually before known traffic events

## Tuning the profiles

The numbers in `options/*.js` are starting guesses. Adjust once you have real signals:

- **`load.js` target** — your actual expected concurrent users at peak. For a single school, count = (active users × concurrency factor). Concurrency factor is usually ~0.1–0.2 for school apps (most students aren't using the app simultaneously).
- **`load.js` thresholds** — after a few green runs, tighten `p(95)` to ~20% above observed baseline. Too loose = regressions slip; too tight = flaky CI.
- **`spike.js` target** — set to ≥10× the `load.js` target. Spike value comes from the *ratio*, not absolute number.

## Scenario

Currently one scenario: [dashboard_flow.js](scenarios/dashboard_flow.js). It logs in once per VU, then loops `GET /api/v1/dashboard` and `GET /api/v1/schedules`. Add scenarios for distinct user flows (e.g. document upload, poll voting) as you go — one scenario per realistic flow beats one per endpoint.
