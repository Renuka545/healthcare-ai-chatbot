import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
from app.models import (
    ChatRequest, ChatResponse, ToolExecutionResult, 
    IntentComparisonResult, EvaluationSummary,
    AppointmentModalPayload, CancelAppointmentRequest
)
from app.intent_engine import IntentDetectionEngine
from app.tools import HealthcareToolRegistry
from app.evaluator import ChatbotEvaluator

app = FastAPI(
    title="Healthcare AI Chatbot with Intelligent Tool Selection & Interactive Action Modal",
    description="Production AI Chatbot for Healthcare Intent Classification, Tool Selection, Pop-up Action Modal, and History Timeline",
    version="1.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
engine = IntentDetectionEngine()
tool_registry = HealthcareToolRegistry()
evaluator = ChatbotEvaluator()

# Mount static directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Healthcare AI Chatbot API is running. Access UI at /static/index.html"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Healthcare AI Chatbot",
        "version": "1.1.0",
        "gemini_api_configured": bool(os.environ.get("GEMINI_API_KEY"))
    }

@app.post("/api/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    """Processes user query, redacts PHI, identifies intent, triggers modal if needed, executes tool, and synthesizes response."""
    sanitized_q, phi_detected = engine.sanitize_query(request.query)
    
    # Classify intent using selected mode (default: hybrid)
    intent_res = engine.classify(request.query, mode=request.classifier_mode or "hybrid")
    
    # Inject patient_id if not present
    if "patient_id" not in intent_res.parameters:
        intent_res.parameters["patient_id"] = request.patient_id or "P-1001"
        
    action_requires_modal = False
    modal_payload = None

    # Check if appointment booking requires modal confirmation & parameter verification
    if intent_res.tool_name == "book_appointment":
        action_requires_modal = True
        extracted_spec = intent_res.parameters.get("specialty", "Cardiology")
        extracted_doc = intent_res.parameters.get("doctor_name", "Dr. Emily Vance")
        extracted_reason = intent_res.parameters.get("reason", request.query)
        
        modal_payload = AppointmentModalPayload(
            specialty=extracted_spec,
            doctor_name=extracted_doc,
            reason=extracted_reason,
            preferred_date="2026-08-17",
            preferred_time="10:00 AM"
        )
        
    # Execute selected healthcare tool
    raw_tool_res = tool_registry.execute_tool(intent_res.tool_name, intent_res.parameters)
    
    tool_exec_res = ToolExecutionResult(
        tool_name=intent_res.tool_name,
        success=raw_tool_res.get("success", True),
        data=raw_tool_res,
        message=raw_tool_res.get("message", "Tool execution complete.")
    )
    
    # Synthesize Final Answer
    final_text = raw_tool_res.get("message", "Request processed.")
    if intent_res.tool_name == "healthcare_rag_qa":
        final_text = raw_tool_res.get("answer", final_text)
    elif intent_res.is_emergency:
        final_text = f"🚨 {final_text}\n\nImmediate Action Recommended: Call 911 or proceed to nearest Emergency Room."
    elif action_requires_modal:
        final_text = f"📅 I have prepared your appointment request! Please review, select your specialist, health concern, and preferred time in the confirmation pop-up screen to complete your booking."

    rag_sources = raw_tool_res.get("sources") if intent_res.tool_name == "healthcare_rag_qa" else None

    return ChatResponse(
        query=request.query,
        intent_info=intent_res,
        tool_result=tool_exec_res,
        final_response=final_text,
        sanitized_query=sanitized_q,
        rag_sources=rag_sources,
        action_requires_modal=action_requires_modal,
        modal_payload=modal_payload
    )

@app.get("/api/history")
def get_patient_history(patient_id: str = Query("P-1001", description="Patient ID")):
    """Retrieves patient action history, appointments, lab results, prescriptions, and tickets."""
    return tool_registry.get_patient_history(patient_id)

@app.post("/api/appointments/cancel")
def cancel_appointment(req: CancelAppointmentRequest):
    """Cancels a scheduled appointment."""
    return tool_registry.cancel_appointment(req.appointment_id, req.patient_id or "P-1001")

@app.post("/api/intents/compare", response_model=IntentComparisonResult)
def compare_intent_methods(request: ChatRequest):
    """Side-by-side comparison of Rule-Based vs LLM-Based vs Hybrid intent classifiers."""
    rule_res = engine.classify_rule_based(request.query)
    llm_res = engine.classify_llm_based(request.query)
    hybrid_res = engine.classify_hybrid(request.query)
    
    recommended = "Hybrid Approach"
    if rule_res.is_emergency:
        recommended = "Hybrid (Rule-Stage Fast Path for Emergency Triage)"
    
    return IntentComparisonResult(
        query=request.query,
        rule_based=rule_res,
        llm_based=llm_res,
        hybrid=hybrid_res,
        recommended_approach=recommended
    )

@app.get("/api/evaluate", response_model=EvaluationSummary)
def run_evaluation_benchmark(method: str = Query("hybrid", description="Method: 'rule', 'llm', or 'hybrid'")):
    """Runs evaluation suite on test dataset and calculates benchmark metrics."""
    return evaluator.run_evaluation(method=method)

@app.get("/api/tools")
def list_registered_tools():
    """Lists available healthcare tools and descriptions."""
    return {
        "tools": [
            {
                "name": "book_appointment",
                "description": "Schedules a doctor/specialist appointment with custom specialist, health problem, doctor, and date/time.",
                "parameters": ["specialty", "doctor_name", "preferred_date", "preferred_time", "reason", "patient_id"]
            },
            {
                "name": "cancel_appointment",
                "description": "Cancels a booked appointment.",
                "parameters": ["appointment_id", "patient_id"]
            },
            {
                "name": "get_lab_results",
                "description": "Retrieves patient laboratory diagnostic reports and blood test results.",
                "parameters": ["patient_id", "test_name"]
            },
            {
                "name": "request_prescription_refill",
                "description": "Processes prescription medication refills with doctor approval workflow.",
                "parameters": ["medication", "pharmacy", "patient_id"]
            },
            {
                "name": "triage_emergency_symptoms",
                "description": "Evaluates medical symptom severity for immediate clinical triage.",
                "parameters": ["symptoms", "severity", "patient_id"]
            },
            {
                "name": "create_support_ticket",
                "description": "Creates a healthcare billing, portal tech support, or administrative ticket.",
                "parameters": ["category", "subject", "priority", "patient_id"]
            },
            {
                "name": "list_support_tickets",
                "description": "Lists patient's existing support tickets.",
                "parameters": ["patient_id"]
            },
            {
                "name": "healthcare_rag_qa",
                "description": "Answers medical FAQs, preparation rules, and clinic policy queries using RAG.",
                "parameters": ["query"]
            }
        ]
    }

@app.get("/api/rag/search")
def search_knowledge_base(q: str = Query(..., description="Medical search query")):
    """Direct search endpoint for healthcare RAG knowledge base."""
    return tool_registry.rag_engine.generate_rag_answer(q)
