import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL } from './config.js';

export function login(email, password) {
  const res = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email, password }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(res, { 'login 200': (r) => r.status === 200 });

  const token = res.json('access_token');
  if (!token) {
    throw new Error(`login failed: ${res.status} ${res.body}`);
  }
  return token;
}
