import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

# Ensure webhook_server directory is in the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webhook_server"))

from server import app, reset_crm_db, load_crm

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup: Reset DB before each test
    reset_crm_db()
    yield
    # Teardown: Reset DB after each test
    reset_crm_db()

def test_verify_customer_success_dob():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_verify_001",
                    "type": "function",
                    "function": {
                        "name": "verify_customer",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "dob": "15-08-1990",
                            "last4PAN": ""
                        }
                    }
                }
            ]
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["toolCallId"] == "tc_verify_001"
    assert data["results"][0]["result"]["verified"] is True
    assert data["results"][0]["result"]["status"] == "SUCCESS"

    # Verify CRM state updated
    crm = load_crm()
    assert crm["cust_rahul_001"]["verification_status"] == "VERIFIED"

def test_verify_customer_success_pan():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_verify_002",
                    "type": "function",
                    "function": {
                        "name": "verify_customer",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "dob": "",
                            "last4PAN": "5241"
                        }
                    }
                }
            ]
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["result"]["verified"] is True

    crm = load_crm()
    assert crm["cust_rahul_001"]["verification_status"] == "VERIFIED"

def test_verify_customer_failure_limits():
    payload_fail = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_verify_fail",
                    "type": "function",
                    "function": {
                        "name": "verify_customer",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "dob": "01-01-2000",
                            "last4PAN": "0000"
                        }
                    }
                }
            ]
        }
    }
    
    # First fail
    response = client.post("/webhook", json=payload_fail)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["result"]["verified"] is False
    crm = load_crm()
    assert crm["cust_rahul_001"]["failed_verification_attempts"] == 1
    assert crm["cust_rahul_001"]["verification_status"] == "UNVERIFIED"

    # Second fail
    response = client.post("/webhook", json=payload_fail)
    assert response.status_code == 200
    crm = load_crm()
    assert crm["cust_rahul_001"]["failed_verification_attempts"] == 2
    assert crm["cust_rahul_001"]["verification_status"] == "FAILED"

def test_log_promise_to_pay():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_ptp_001",
                    "type": "function",
                    "function": {
                        "name": "log_promise_to_pay",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "ptp_date": "2026-08-20",
                            "ptp_amount": 8499
                        }
                    }
                }
            ]
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["result"]["status"] == "SUCCESS"
    assert "ptp_id" in data["results"][0]["result"]

    crm = load_crm()
    assert crm["cust_rahul_001"]["promise_to_pay_date"] == "2026-08-20"
    assert crm["cust_rahul_001"]["promise_to_pay_amount"] == 8499
    assert crm["cust_rahul_001"]["status"] == "PTP"

def test_send_payment_link():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_send_link",
                    "type": "function",
                    "function": {
                        "name": "send_payment_link",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "payment_method": "UPI"
                        }
                    }
                }
            ]
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["result"]["status"] == "SUCCESS"

    crm = load_crm()
    assert crm["cust_rahul_001"]["payment_link_sent"] is True
    assert crm["cust_rahul_001"]["payment_link_method"] == "UPI"

def test_mark_disposition():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_disp",
                    "type": "function",
                    "function": {
                        "name": "mark_disposition",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "disposition_code": "PTP",
                            "call_notes": "Customer agreed to pay tomorrow."
                        }
                    }
                }
            ]
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["result"]["status"] == "RECORDED"

    crm = load_crm()
    assert crm["cust_rahul_001"]["disposition_code"] == "PTP"
    assert crm["cust_rahul_001"]["call_notes"] == "Customer agreed to pay tomorrow."
    assert crm["cust_rahul_001"]["calls_count"] == 1

def test_escalate_to_agent():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "tc_escalate",
                    "type": "function",
                    "function": {
                        "name": "escalate_to_agent",
                        "arguments": {
                            "customer_id": "cust_rahul_001",
                            "reason": "Dispute"
                        }
                    }
                }
            ]
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["result"]["status"] == "TRANSFER_INITIATED"

    crm = load_crm()
    assert crm["cust_rahul_001"]["disposition_code"] == "ESCALATED_DISPUTE"
    assert crm["cust_rahul_001"]["status"] == "ESCALATED"
