// Simulates a sudden traffic burst 
export const options = {
  stages: [
    { duration: '30s', target: 5 },     // baseline
    { duration: '20s', target: 500 },   // spike
    { duration: '1m',  target: 500 },   // hold the peak briefly
    { duration: '20s', target: 5 },     // drop back to baseline
    { duration: '2m',  target: 5 },     // recovery window
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<3000'],
  },
};
