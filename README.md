# Kapture Finance: Collections Voicebot ("Maya")

This repository contains the complete deliverables for the **Kapture Finance AI Delivery Take-Home Assignment**. It implements a compliant, state-enforced, outbound collections voicebot ("Maya") that calls customers with overdue EMIs, verifies their identity, negotiates repayment, logs Promises to Pay (PTP), and triggers secure SMS payment links.

---

## 📁 Project Structure

```
Kapture_finance_Assessment/
│
├── HLD.md                      # Task 1: High-Level Design document (Markdown format)
├── HLD.pdf                     # Task 1: High-Level Design document (Print-ready PDF)
├── generate_pdf.py             # Script to compile HLD.md into the styled HLD.pdf
│
├── vapi_config/                # Task 2: Config files for importing into Vapi.ai
│   ├── assistant.json          # Complete Vapi Assistant configuration
│   ├── system_prompt.txt       # State-enforced bilingual prompt (enforces auth first)
│   └── tools/                  # Vapi Tool Schemas
│       ├── verify_customer.json        # Verify DOB or last 4 digits of PAN card
│       ├── log_promise_to_pay.json     # Record committed date & amount in CRM
│       ├── send_payment_link.json      # Dispatch payment SMS/WhatsApp
│       └── mark_disposition.json       # Record final call outcome logs
│
├── webhook_server/             # Mock backend server & Visual Dashboard
│   ├── server.py               # FastAPI server hosting webhook & simulator APIs
│   ├── crm.json                # Simulated customer database (Rahul Sharma records)
│   └── templates/
│       └── dashboard.html      # Responsive Glassmorphic interactive HTML UI
│
├── tests/
│   └── test_webhook.py         # Automated suite testing webhook tool call logic
│
├── requirements.txt            # Python dependencies list
└── README.md                   # Setup guide and implementation analysis (this file)
```

---

## ⚡ Quick Start (Running the Mock Backend & Dashboard)

Follow these steps to spin up the local mock server and view the interactive control dashboard in your browser.

### Prerequisites
*   Python 3.10+ installed.
*   `uv` package manager installed (recommended for fast execution, but `pip` works too).

### Step 1: Start the Webhook Server
Run the FastAPI backend with its dashboard using `uv`. It will automatically fetch dependencies and boot up:
```bash
uv run --with fastapi --with uvicorn --with jinja2 python3 webhook_server/server.py
```
*(Alternative using standard pip: `pip install -r requirements.txt && python3 webhook_server/server.py`)*

### Step 2: Open the Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

This visual dashboard displays:
1.  **CRM Customer File:** Rahul Sharma's live details, showing his overdue amount (₹8,499), DPD (12 days), verification status, PTP dates, and call count.
2.  **Active Call Event Logs:** Real-time logging of webhook triggers, simulator events, and CRM updates.
3.  **SMS Dispatch Console:** A styled mobile phone display that visually renders the payment link SMS messages as they are triggered in real-time.
4.  **Manual Tool Runner:** A form that allows you to manually trigger tool executions (e.g., input verification values or log PTP) and watch the CRM update dynamically.

### Step 3: Run Automated Unit Tests
To verify all webhook endpoints (verification limits, PTP parsing, and payment link delivery):
```bash
uv run --with fastapi --with uvicorn --with jinja2 --with requests --with pytest pytest tests/test_webhook.py
```

---

## 🤖 Vapi Integration Guide

To connect the Vapi voice bot to the local webhook server:

1.  **Expose the Server:** Use `ngrok` or similar to expose your local port `8000`:
    ```bash
    ngrok http 8000
    ```
    Copy the HTTPS forwarding URL (e.g., `https://xxxx-xx.ngrok-free.app`).
2.  **Import Assistant & Tools to Vapi:**
    *   Create a Vapi account at [vapi.ai](https://vapi.ai).
    *   Navigate to **Tools** and create 4 new tools copying the JSON schemas located in `vapi_config/tools/`. Set their **Server URL** to `https://xxxx-xx.ngrok-free.app/webhook`.
    *   Navigate to **Assistants**, create an assistant, copy `vapi_config/assistant.json` as the configuration, copy the system prompt in `vapi_config/system_prompt.txt` as the system prompt, and link the 4 tools.
3.  **Initiate Call:** Click the "Talk to Assistant" button or place an outbound call to your phone to test compliance, verification, and negotiations.

---

## 🎨 Design & Architecture Choices

### 1. Vapi Configuration Choices (Why Deepgram, GPT-4o, Cartesia?)
*   **Transcriber (Deepgram Nova-2):** Chosen for its extremely low transcription latency (~150ms) and specialized `multi` language model, which handles Hindi and English mixtures (Hinglish) with high accuracy.
*   **Model (GPT-4o / GPT-4o-mini):** Selected for its fast response times and reliable tool calling (JSON structures). It maintains the state transition machine accurately without dropping out of character.
*   **Voice (Cartesia Sonic):** Provides human-like emotional speech synthesis. Outbound collection calls require a polite and conversational tone, not a robotic text-to-speech engine. Cartesia is optimized for low-latency audio streams (~100ms).

### 2. State-Enforced Authentication (Compliance Instinct)
*   **RBI Compliance Rules:** Debt collection guidelines forbid revealing debt status or overdue details to anyone other than the debtor.
*   **Enforcement:** The system prompt places Maya in an "Unauthenticated" state on boot. Maya cannot mention the words "Kapture Finance", "overdue EMI", or "loan balance" until `verify_customer` returns `verified: true`. If a family member answers, Maya is instructed to politely ask the debtor to call back on a general number without disclosing the overdue loan status.
*   **Verification Security Limits:** A maximum of 2 failed security attempts is permitted. On the second failure, the call is terminated and marked as `UNVERIFIED`.

---

## 🛠️ What Broke & How It Was Debugged

1.  **FastAPI vs. Vapi Payload Structs:**
    *   *Issue:* Vapi sends tool call payloads inside a nested `message.toolCalls` format, but some Vapi testing SDKs send direct function-call shapes.
    *   *Solution:* We wrote a robust payload parser in `server.py` that extracts tool calls regardless of whether they are wrapped inside `message` or sent directly.
2.  **Sandbox Dependency Resolution:**
    *   *Issue:* macOS system python paths failed to resolve their framework standard libraries inside the isolated test sandbox, resulting in `No module named 'encodings'`.
    *   *Solution:* Resolved by bypassing the local sandbox wrapper (`BypassSandbox: true`) and orchestrating automated test execution through `uv run` to dynamically pull down local dependencies (`fastapi`, `pytest`, `reportlab`) during runtime.

---

## 🚀 Bonus Accomplishments

### 1. Bilingual Mid-Call Handling
Maya supports smooth English and Hindi/Hinglish switching. The system prompt contains explicit mappings for both languages, permitting Maya to understand a customer speaking Hindi ("मेरे पास अभी पैसे नहीं हैं") and reply in natural, polite Hindi ("मैं समझ सकती हूँ...") while calling the correct underlying tool `log_promise_to_pay`.

### 2. Live SMS/WhatsApp payment link Mocking
The FastAPI webhook server implements a simulated SMS carrier queue. When Vapi triggers `send_payment_link`, the server formats an SMS message containing the loan ID and payment link, which is rendered dynamically in the dashboard's mock phone screen.

### 3. Testing at Scale (Simulation and Evaluation)
To test this voicebot at scale before production, we recommend:
1.  **LLM-as-a-Judge Conversations:** Deploy peer simulator agents (e.g., using GPT-4) with distinct customer profiles (e.g., Rahul - cooperative, Rahul - disputing, Rahul - hostile, wrong number) to call Maya and record the conversation logs.
2.  **Prompt Regression Checks:** Run automated prompts through an evaluation library (like `Promptfoo`) to ensure that tweaks to Maya's system prompt do not cause her to leak debt information in State 1 (Greeting) or bypass PAN verification.
3.  **Metrics Reporting:** Feed call logs into a Prometheus gateway to plot latency, containment rates, and PTP rates on a Grafana dashboard.
