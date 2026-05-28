
export const options = {
  stages: [
    { duration: '1m',  target: 80 },   // ramp to average
    { duration: '3m',  target: 80 },   // hold at average
    { duration: '1m',  target: 120 },  // ramp to peak
    { duration: '2m',  target: 120 },  // hold at peak
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
  },
};
