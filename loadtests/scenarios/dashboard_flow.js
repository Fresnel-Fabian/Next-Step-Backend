// Mixed read workload: login once per VU, then hit dashboard + schedules.
// Profile is selected by PROFILE env var (load | stress | soak).
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { login } from '../lib/auth.js';
import { BASE_URL, TEST_USER, TEST_PASS } from '../lib/config.js';

const profile = __ENV.PROFILE || 'load';
import { options as loadOptions } from '../options/load.js';
import { options as stressOptions } from '../options/stress.js';
import { options as soakOptions } from '../options/soak.js';
import { options as spikeOptions } from '../options/spike.js';
const profiles = {
  load: loadOptions,
  stress: stressOptions,
  soak: soakOptions,
  spike: spikeOptions,
};
export const options = profiles[profile];

export function setup() {
  const token = login(TEST_USER, TEST_PASS);
  return { token };
}

export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  group('dashboard', () => {
    const res = http.get(`${BASE_URL}/api/v1/dashboard`, { headers });
    check(res, { 'dashboard 200': (r) => r.status === 200 });
  });

  group('schedules', () => {
    const res = http.get(`${BASE_URL}/api/v1/schedules`, { headers });
    check(res, { 'schedules 200': (r) => r.status === 200 });
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data),
  };
}

function textSummary(data) {
  const m = data.metrics;
  const p95 = m.http_req_duration?.values?.['p(95)']?.toFixed(0) ?? 'n/a';
  const p99 = m.http_req_duration?.values?.['p(99)']?.toFixed(0) ?? 'n/a';
  const errRate = ((m.http_req_failed?.values?.rate ?? 0) * 100).toFixed(2);
  const reqs = m.http_reqs?.values?.count ?? 0;
  return `\n  reqs=${reqs}  errors=${errRate}%  p95=${p95}ms  p99=${p99}ms\n`;
}
