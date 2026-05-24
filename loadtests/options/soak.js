export const options = {
  stages: [
    { duration: '5m', target: 40 },
    { duration: '3h', target: 40 },
    { duration: '5m', target: 0 },
  ],
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
};
