import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  // stages: [
  //   { duration: '1m', target: 50 },   // ramp up
  //   { duration: '3m', target: 50 },   // hold steady load
  //   { duration: '1m', target: 200 },  // spike
  //   { duration: '3m', target: 200 },  // hold spike
  //   { duration: '1m', target: 0 },    // ramp down
  // ],
  stages: [
  { duration: '10s', target: 50 },   // ramp up
  { duration: '20s', target: 50 },   // hold steady load
  { duration: '10s', target: 200 },  // spike
  { duration: '20s', target: 200 },  // hold spike
  { duration: '10s', target: 0 },    // ramp down
],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests under 500ms
    errors: ['rate<0.01'],            // error rate under 1%
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/health`);

  const ok = check(res, {
    'status is 200':        (r) => r.status === 200,
    'status field is ok':   (r) => r.json('status') === 'ok',
    'has version field':    (r) => r.json('version') !== undefined,
    'has timestamp field':  (r) => r.json('timestamp') !== undefined,
    'response time < 500ms':(r) => r.timings.duration < 500,
  });

  errorRate.add(!ok);
  sleep(1);
}

// """"
// stages: [
//   { duration: '5m',  target: 500  },  // ramp up
//   { duration: '30m', target: 500  },  // hold — this generates ~1M req at 500 VUs
//   { duration: '5m',  target: 0    },  // ramp down
// ],
// """

// # import pytest
// # from httpx import AsyncClient
// # from app.main import app

// # @pytest.mark.asyncio
// # async def test_health_check_endpoint():
// #     """Smoke test for the health check endpoint."""
// #     async with AsyncClient(app=app, base_url="http://test") as ac:
// #         response = await ac.get("/health")
    
// #     assert response.status_code == 200
// #     data = response.json()
// #     assert data["status"] == "ok"
// #     assert "version" in data
// #     assert "timestamp" in data
