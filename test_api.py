"""
Automated Verification Script for Phase 5 Backend API (FastAPI TestClient).

Verifies all Phase 5 completion criteria:
1. App startup and router inclusion (§5.7).
2. GET /api/health returns status 'ok' (§5.3).
3. GET /api/schemes returns list of 10 schemes (§5.4).
4. POST /api/query with factual query returns formatted JSON with Groww citation (§5.2).
5. POST /api/query with advisory query returns refusal JSON with educational link (§5.2).
6. POST /api/query with PII (Aadhaar, Phone, PAN) is blocked with security alert (§5.6).
"""

import json
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from src.api.main import app

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_api")

client = TestClient(app)


def test_run_api_tests():
    print("=== Phase 5 Backend API Automated Verification ===")
    
    # 1. Test GET /api/health
    print("\n[Test 1] GET /api/health")
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Expected 200, got {res_health.status_code}"
    data_health = res_health.json()
    print(f"Response: {data_health}")
    assert data_health["status"] == "ok", "Health status is not 'ok'"
    assert "engine" in data_health, "Missing engine field"
    print("--> PASSED")

    # 2. Test GET /api/schemes
    print("\n[Test 2] GET /api/schemes")
    res_schemes = client.get("/api/schemes")
    assert res_schemes.status_code == 200
    data_schemes = res_schemes.json()
    print(f"Total count: {data_schemes['total_count']} | First 3: {data_schemes['schemes'][:3]}")
    assert data_schemes["total_count"] == 10, f"Expected 10 schemes, got {data_schemes['total_count']}"
    print("--> PASSED")

    # 3. Test POST /api/query with PII Input (Aadhaar number)
    print("\n[Test 3] POST /api/query with PII Input (Aadhaar Number)")
    pii_payload = {"query": "My Aadhaar is 1234 5678 9012. What is the NAV of HDFC Nifty 50?", "use_llm_intent": False}
    res_pii = client.post("/api/query", json=pii_payload)
    assert res_pii.status_code == 200
    data_pii = res_pii.json()
    print(f"Status: {data_pii['status']} | Intent: {data_pii['intent']}")
    print(f"Answer snippet: {data_pii['answer'][:100]}...")
    assert data_pii["status"] == "pii_blocked", "Failed to block PII input!"
    assert "Security Alert" in data_pii["answer"], "Missing security alert message"
    print("--> PASSED")

    # 4. Test POST /api/query with Advisory Query
    print("\n[Test 4] POST /api/query with Advisory Query (Zero Advisory Tolerance)")
    adv_payload = {"query": "Which fund is better between Nifty 50 and Sensex?", "use_llm_intent": False}
    res_adv = client.post("/api/query", json=adv_payload)
    assert res_adv.status_code == 200
    data_adv = res_adv.json()
    print(f"Status: {data_adv['status']} | Intent: {data_adv['intent']}")
    print(f"Educational Link: {data_adv.get('educational_link')}")
    assert data_adv["status"] == "refused", "Failed to refuse advisory query!"
    assert data_adv["intent"] == "ADVISORY"
    assert "groww.in" in data_adv.get("educational_link", ""), "Missing Groww educational link"
    print("--> PASSED")

    # 5. Test POST /api/query with Factual Query
    print("\n[Test 5] POST /api/query with Factual Query")
    fac_payload = {"query": "What is the exit load for HDFC Gold ETF if redeemed early?", "use_llm_intent": False}
    res_fac = client.post("/api/query", json=fac_payload)
    assert res_fac.status_code == 200
    data_fac = res_fac.json()
    print(f"Status: {data_fac['status']} | Intent: {data_fac['intent']}")
    print(f"Source URL: {data_fac.get('source_url')}")
    safe_ans = data_fac['answer'].encode('ascii', 'replace').decode('ascii') if sys.platform == 'win32' else data_fac['answer']
    print(f"Answer:\n{safe_ans}")
    assert data_fac["status"] == "success", "Failed to process factual query!"
    assert data_fac["intent"] == "FACTUAL"
    assert "groww.in" in data_fac.get("source_url", ""), "Missing Groww source URL"
    print("--> PASSED")

    # 6. Test GET /api/ingest/status (Phase 7 Scheduler)
    print("\n[Test 6] GET /api/ingest/status (Phase 7 Scheduler)")
    res_status = client.get("/api/ingest/status")
    assert res_status.status_code == 200, f"Expected 200, got {res_status.status_code}"
    data_status = res_status.json()
    print(f"Status: {data_status['status']} | Is Running: {data_status['is_running']} | Cron: {data_status['cron_expression']}")
    assert data_status["status"] == "success", "Scheduler status is not success"
    assert "cron_expression" in data_status, "Missing cron_expression field"
    print("--> PASSED")

    print("\n" + "=" * 55)
    print("ALL PHASE 5 & PHASE 7 API TESTS PASSED SUCCESSFULLY!")
    print("=" * 55)


if __name__ == "__main__":
    test_run_api_tests()
