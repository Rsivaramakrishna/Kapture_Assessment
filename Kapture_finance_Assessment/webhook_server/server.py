import os
import json
import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Kapture Finance Webhook Server", version="1.0.0")

# Setup Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
CRM_FILE_PATH = os.path.join(BASE_DIR, "crm.json")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# In-Memory Logs for the Session
SMS_LOGS = []
CALL_EVENTS = []

# Load CRM database
def load_crm() -> Dict[str, Any]:
    if not os.path.exists(CRM_FILE_PATH):
        # Fallback if file doesn't exist
        default_crm = {
            "cust_rahul_001": {
                "customer_id": "cust_rahul_001",
                "name": "Rahul Sharma",
                "phone": "+91 98765 43210",
                "loan_id": "LN-KAP-88220",
                "overdue_emi_amount": 8499.0,
                "due_date": "2026-08-05",
                "days_past_due": 12,
                "dob": "15-08-1990",
                "last4PAN": "5241",
                "status": "OVERDUE",
                "verification_status": "UNVERIFIED",
                "failed_verification_attempts": 0,
                "promise_to_pay_date": null,
                "promise_to_pay_amount": null,
                "payment_link_sent": false,
                "payment_link_method": null,
                "disposition_code": null,
                "call_notes": null,
                "calls_count": 0
            }
        }
        with open(CRM_FILE_PATH, "w") as f:
            json.dump(default_crm, f, indent=2)
        return default_crm
    
    with open(CRM_FILE_PATH, "r") as f:
        return json.load(f)

# Save CRM database
def save_crm(crm_data: Dict[str, Any]):
    with open(CRM_FILE_PATH, "w") as f:
        json.dump(crm_data, f, indent=2)

# Reset CRM to defaults
def reset_crm_db():
    default_crm = {
        "cust_rahul_001": {
            "customer_id": "cust_rahul_001",
            "name": "Rahul Sharma",
            "phone": "+91 98765 43210",
            "loan_id": "LN-KAP-88220",
            "overdue_emi_amount": 8499.0,
            "due_date": "2026-08-05",
            "days_past_due": 12,
            "dob": "15-08-1990",
            "last4PAN": "5241",
            "status": "OVERDUE",
            "verification_status": "UNVERIFIED",
            "failed_verification_attempts": 0,
            "promise_to_pay_date": None,
            "promise_to_pay_amount": None,
            "payment_link_sent": False,
            "payment_link_method": None,
            "disposition_code": None,
            "call_notes": None,
            "calls_count": 0
        }
    }
    save_crm(default_crm)
    SMS_LOGS.clear()
    CALL_EVENTS.clear()
    log_call_event("SYSTEM", "Database and SMS queue reset to defaults.")

def log_call_event(source: str, message: str):
    timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
    CALL_EVENTS.append({
        "timestamp": timestamp,
        "source": source,
        "message": message
    })

# API Routes
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    crm_data = load_crm()
    rahul = crm_data.get("cust_rahul_001", {})
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "crm": rahul,
            "sms_logs": SMS_LOGS,
            "call_events": CALL_EVENTS
        }
    )

@app.get("/api/crm")
async def get_crm_api():
    crm_data = load_crm()
    return JSONResponse(content=crm_data.get("cust_rahul_001", {}))

@app.get("/api/sms-logs")
async def get_sms_logs():
    return JSONResponse(content=SMS_LOGS)

@app.get("/api/call-logs")
async def get_call_logs():
    return JSONResponse(content=CALL_EVENTS)

@app.post("/api/reset")
async def reset_crm_api():
    reset_crm_db()
    return JSONResponse(content={"status": "success", "message": "CRM reset successfully."})

# Unified Webhook handler for Vapi Tool Calls
@app.post("/webhook")
async def handle_vapi_webhook(request: Request):
    payload = await request.json()
    
    # Identify message type
    # Vapi sends JSON body containing a 'message' field
    message_data = payload.get("message", {})
    message_type = message_data.get("type")
    
    # Fallback to direct tool call structure if Vapi sends direct function call
    if not message_type and "toolCalls" in payload:
        message_data = payload
        message_type = "tool-calls"
    elif not message_type and "function" in payload:
        message_data = {"toolCalls": [payload]}
        message_type = "tool-calls"

    # We only care about "tool-calls" type
    if message_type != "tool-calls":
        return JSONResponse(content={"status": "ignored", "message": f"Ignored event type: {message_type}"})

    tool_calls = message_data.get("toolCalls", [])
    results = []

    crm_data = load_crm()
    rahul = crm_data.get("cust_rahul_001", {})

    for call in tool_calls:
        call_id = call.get("id")
        func_data = call.get("function", {})
        func_name = func_data.get("name")
        args = func_data.get("arguments", {})

        log_call_event("BOT (TOOL CALL)", f"Invoking tool: {func_name} with arguments: {json.dumps(args)}")

        result_content = {}

        if func_name == "verify_customer":
            customer_id = args.get("customer_id")
            dob_input = args.get("dob", "").strip()
            pan_input = args.get("last4PAN", "").strip()

            # Clean inputs for matching
            dob_clean = dob_input.replace("-", "").replace("/", "").replace(" ", "")
            dob_expected = rahul.get("dob", "").replace("-", "")

            dob_match = False
            if dob_clean and dob_expected:
                # Direct string match or containing matches
                dob_match = dob_clean in dob_expected or dob_expected in dob_clean
            
            pan_match = False
            if pan_input and rahul.get("last4PAN"):
                pan_match = pan_input in rahul.get("last4PAN") or rahul.get("last4PAN") in pan_input

            if dob_match or pan_match:
                rahul["verification_status"] = "VERIFIED"
                rahul["failed_verification_attempts"] = 0
                result_content = {
                    "status": "SUCCESS",
                    "verified": True,
                    "message": "Identity verification successful. Debt information can now be disclosed."
                }
                log_call_event("SYSTEM (CRM)", f"Customer verified successfully. Details: DOB match={dob_match}, PAN match={pan_match}.")
            else:
                attempts = rahul.get("failed_verification_attempts", 0) + 1
                rahul["failed_verification_attempts"] = attempts
                if attempts >= 2:
                    rahul["verification_status"] = "FAILED"
                
                result_content = {
                    "status": "FAILED",
                    "verified": False,
                    "message": f"Verification failed. Attempt {attempts} of 2."
                }
                log_call_event("SYSTEM (CRM)", f"Verification failed. Attempt {attempts}/2. Input: DOB='{dob_input}', PAN='{pan_input}'")

        elif func_name == "log_promise_to_pay":
            customer_id = args.get("customer_id")
            ptp_date = args.get("ptp_date")
            ptp_amount = args.get("ptp_amount")

            # Update CRM status
            rahul["promise_to_pay_date"] = ptp_date
            rahul["promise_to_pay_amount"] = ptp_amount
            rahul["status"] = "PTP"
            
            ptp_id = f"ptp_log_{int(datetime.datetime.now().timestamp())}"
            result_content = {
                "status": "SUCCESS",
                "ptp_id": ptp_id
            }
            log_call_event("SYSTEM (CRM)", f"Logged Promise to Pay. Date: {ptp_date}, Amount: ₹{ptp_amount}")

        elif func_name == "send_payment_link":
            customer_id = args.get("customer_id")
            payment_method = args.get("payment_method", "Any")

            rahul["payment_link_sent"] = True
            rahul["payment_link_method"] = payment_method
            
            # Simulate sending SMS
            timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
            sms_text = (
                f"Dear Rahul Sharma, your payment link for Kapture Finance loan {rahul.get('loan_id')} "
                f"is https://pay.kapture.in/pay/LN88220. Please clear your overdue EMI of ₹{rahul.get('overdue_emi_amount')} today."
            )
            
            SMS_LOGS.append({
                "timestamp": timestamp,
                "to": rahul.get("phone"),
                "message": sms_text,
                "channel": "SMS & WhatsApp"
            })
            
            result_content = {
                "status": "SUCCESS",
                "delivery_channel": "SMS & WhatsApp sent successfully."
            }
            log_call_event("SYSTEM (SMS)", f"SMS payment link dispatched to {rahul.get('phone')} for mode: {payment_method}")

        elif func_name == "mark_disposition":
            customer_id = args.get("customer_id")
            disposition = args.get("disposition_code")
            notes = args.get("call_notes")

            rahul["disposition_code"] = disposition
            rahul["call_notes"] = notes
            
            # Increment call count
            rahul["calls_count"] = rahul.get("calls_count", 0) + 1
            
            result_content = {
                "status": "RECORDED"
            }
            log_call_event("SYSTEM (CRM)", f"Call disposition marked: {disposition}. Notes: {notes}")
            
        elif func_name == "escalate_to_agent":
            customer_id = args.get("customer_id")
            reason = args.get("reason")
            
            # Update CRM status
            rahul["disposition_code"] = f"ESCALATED_{reason.upper()}"
            rahul["status"] = "ESCALATED"
            
            result_content = {
                "status": "TRANSFER_INITIATED",
                "queue_id": "queue_supervisor_tier1"
            }
            log_call_event("SYSTEM (TELEPHONY)", f"Transferring call to human supervisor. Reason: {reason}")

        else:
            # Unknown tool
            result_content = {"status": "ERROR", "message": f"Tool '{func_name}' not recognized."}
            log_call_event("SYSTEM (ERROR)", f"Unknown tool invocation attempt: {func_name}")

        results.append({
            "toolCallId": call_id,
            "result": result_content
        })

    # Save changes back to CRM
    crm_data["cust_rahul_001"] = rahul
    save_crm(crm_data)

    # Return responses to Vapi
    return JSONResponse(content={"results": results})

# Local Call Simulator API (simulates webhook tool calls via the dashboard)
@app.post("/api/simulate-tool")
async def simulate_tool_api(request: Request):
    payload = await request.json()
    tool_name = payload.get("name")
    args = payload.get("arguments", {})
    
    # Package into toolCalls structure
    mock_payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": f"sim_call_{int(datetime.datetime.now().timestamp())}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": args
                    }
                }
            ]
        }
    }
    
    # Directly invoke the handle_vapi_webhook logic
    # In FastAPI, we can construct a mock Request or just reuse the code.
    # To keep it simple, let's call a internal python function
    crm_data = load_crm()
    rahul = crm_data.get("cust_rahul_001", {})
    
    log_call_event("SIMULATOR", f"Triggered tool simulation: {tool_name} with {json.dumps(args)}")
    
    result_content = {}
    
    if tool_name == "verify_customer":
        dob_input = args.get("dob", "").strip()
        pan_input = args.get("last4PAN", "").strip()
        
        dob_clean = dob_input.replace("-", "").replace("/", "").replace(" ", "")
        dob_expected = rahul.get("dob", "").replace("-", "")

        dob_match = (dob_clean and dob_clean in dob_expected) or (dob_expected and dob_expected in dob_clean)
        pan_match = (pan_input and pan_input in rahul.get("last4PAN", "")) or (rahul.get("last4PAN") and rahul.get("last4PAN") in pan_input)

        if dob_match or pan_match:
            rahul["verification_status"] = "VERIFIED"
            rahul["failed_verification_attempts"] = 0
            result_content = {"verified": True, "message": "Verification successful."}
            log_call_event("SYSTEM (CRM)", "Customer verified successfully.")
        else:
            attempts = rahul.get("failed_verification_attempts", 0) + 1
            rahul["failed_verification_attempts"] = attempts
            if attempts >= 2:
                rahul["verification_status"] = "FAILED"
            result_content = {"verified": False, "message": f"Verification failed. Attempt {attempts}/2."}
            log_call_event("SYSTEM (CRM)", f"Verification failed ({attempts}/2).")

    elif tool_name == "log_promise_to_pay":
        ptp_date = args.get("ptp_date")
        ptp_amount = args.get("ptp_amount")
        rahul["promise_to_pay_date"] = ptp_date
        rahul["promise_to_pay_amount"] = ptp_amount
        rahul["status"] = "PTP"
        result_content = {"status": "SUCCESS", "ptp_id": "ptp_sim_123"}
        log_call_event("SYSTEM (CRM)", f"PTP logged for {ptp_date}.")

    elif tool_name == "send_payment_link":
        method = args.get("payment_method", "Any")
        rahul["payment_link_sent"] = True
        rahul["payment_link_method"] = method
        
        timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
        sms_text = f"Dear Rahul Sharma, your payment link for Kapture Finance loan LN-KAP-88220 is https://pay.kapture.in/pay/LN88220. Please clear your overdue EMI of ₹8499 today."
        SMS_LOGS.append({
            "timestamp": timestamp,
            "to": rahul.get("phone"),
            "message": sms_text,
            "channel": "SMS & WhatsApp"
        })
        result_content = {"status": "SUCCESS"}
        log_call_event("SYSTEM (SMS)", "SMS payment link dispatched.")

    elif tool_name == "mark_disposition":
        disp = args.get("disposition_code")
        notes = args.get("call_notes")
        rahul["disposition_code"] = disp
        rahul["call_notes"] = notes
        rahul["calls_count"] = rahul.get("calls_count", 0) + 1
        result_content = {"status": "RECORDED"}
        log_call_event("SYSTEM (CRM)", f"Call disposition marked: {disp}.")

    elif tool_name == "escalate_to_agent":
        reason = args.get("reason")
        rahul["disposition_code"] = f"ESCALATED_{reason.upper()}"
        rahul["status"] = "ESCALATED"
        result_content = {"status": "TRANSFER_INITIATED"}
        log_call_event("SYSTEM (TELEPHONY)", f"Call escalated. Reason: {reason}.")

    crm_data["cust_rahul_001"] = rahul
    save_crm(crm_data)
    
    return JSONResponse(content={"status": "success", "result": result_content})

if __name__ == "__main__":
    import uvicorn
    # Make sure database exists on boot
    load_crm()
    print("Booting Kapture Finance Webhook server on http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
