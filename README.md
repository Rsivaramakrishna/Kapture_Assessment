📁 Project Deliverables in Workspace
Task 1: High-Level Design (HLD)
HLD.md
 — Concise Markdown document containing system architecture sequences, state transitions, latency budgets, intents, tool definitions, security compliance rules (RBI), and observability KPIs.
HLD.pdf
 — A print-ready, professional PDF of the design document generated dynamically.
generate_pdf.py
 — Python compilation script.
Task 2: Vapi Voice Agent Configurations
assistant.json
 — Importable Vapi assistant configuration.
system_prompt.txt
 — Compliant system prompt that enforces authentication (DOB or PAN verification) in State 1 and State 2 before disclosing any debt information. Supports seamless English/Hindi code-switching.
Tool JSON Schemas (Vapi specs):
verify_customer.json
log_promise_to_pay.json
send_payment_link.json
mark_disposition.json
Mock Webhook Server & Interactive Web Dashboard
server.py
 — FastAPI backend that processes Vapi webhook tool calls, manages the CRM state, and logs call metrics.
dashboard.html
 — Elegant, dark-mode Glassmorphism web dashboard. Displays CRM status, live webhook call logs, and features an interactive manual tool runner and a visual mobile device simulator to watch SMS payment links arrive in real-time.
crm.json
 — Mock database containing debtor Rahul Sharma's loan details.
Verification and Documentation
test_webhook.py
 — Automated test suite verifying tool execution, authentication locking, limit thresholds, and CRM writebacks.
requirements.txt
 — Dependency list.




