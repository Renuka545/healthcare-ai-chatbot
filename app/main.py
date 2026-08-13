import os

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from app.models import (
    ChatRequest,
    ChatResponse,
    ToolExecutionResult,
    IntentComparisonResult,
    EvaluationSummary,
    AppointmentModalPayload,
    CancelAppointmentRequest
)

from app.intent_engine import IntentDetectionEngine
from app.tools import HealthcareToolRegistry
from app.evaluator import ChatbotEvaluator


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = FastAPI(
    title="Healthcare AI Chatbot with Intelligent Tool Selection & Interactive Action Modal",
    description=(
        "Production AI Chatbot for Healthcare Intent Classification, "
        "Tool Selection, RAG, Interactive Action Modal, "
        "and Patient History Timeline"
    ),
    version="1.2.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CORE SERVICES
# ============================================================

engine = IntentDetectionEngine()
tool_registry = HealthcareToolRegistry()
evaluator = ChatbotEvaluator()


# ============================================================
# STATIC FILE CONFIGURATION
# ============================================================

base_dir = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

static_dir = os.path.join(
    base_dir,
    "static"
)

if not os.path.exists(static_dir):
    os.makedirs(static_dir)


app.mount(
    "/static",
    StaticFiles(directory=static_dir),
    name="static"
)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def read_root():
    """
    Serves the chatbot frontend.
    """

    index_file = os.path.join(
        static_dir,
        "index.html"
    )

    if os.path.exists(index_file):
        return FileResponse(index_file)

    return {
        "message": (
            "Healthcare AI Chatbot API is running. "
            "Access UI at /static/index.html"
        )
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    """
    Returns application health and Gemini configuration status.
    """

    return {
        "status": "healthy",
        "service": "Healthcare AI Chatbot",
        "version": "1.2.0",
        "gemini_api_configured": bool(
            os.environ.get("GEMINI_API_KEY")
        )
    }


# ============================================================
# LAB RESULT FORMATTER
# ============================================================

def format_lab_results(
    lab_results,
    patient_id: str
) -> str:
    """
    Converts structured laboratory records into a
    readable chatbot response.

    The formatter supports multiple possible field
    names so that minor differences in the patient
    JSON structure do not break the response.
    """

    if not lab_results:
        return (
            f"🧪 No laboratory results were found "
            f"for patient {patient_id}."
        )

    lines = [
        "🧪 Laboratory Results",
        "",
        f"Patient ID: {patient_id}",
        f"Records Found: {len(lab_results)}",
        ""
    ]

    for index, lab in enumerate(
        lab_results,
        start=1
    ):

        lines.append(
            f"--- Result {index} ---"
        )

        # ----------------------------------------------------
        # Test name
        # ----------------------------------------------------

        test_name = (
            lab.get("test_name")
            or lab.get("test")
            or lab.get("test_type")
            or lab.get("name")
            or "N/A"
        )

        lines.append(
            f"Test: {test_name}"
        )

        # ----------------------------------------------------
        # Result / Value
        # ----------------------------------------------------

        result_value = (
            lab.get("result")
            or lab.get("value")
            or lab.get("result_value")
            or lab.get("test_result")
            or "N/A"
        )

        lines.append(
            f"Result: {result_value}"
        )

        # ----------------------------------------------------
        # Unit
        # ----------------------------------------------------

        unit = lab.get("unit")

        if unit:
            lines.append(
                f"Unit: {unit}"
            )

        # ----------------------------------------------------
        # Reference range
        # ----------------------------------------------------

        reference_range = (
            lab.get("reference_range")
            or lab.get("normal_range")
            or lab.get("reference")
        )

        if reference_range:
            lines.append(
                f"Reference Range: {reference_range}"
            )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status = lab.get("status")

        if status:
            lines.append(
                f"Status: {status}"
            )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        test_date = (
            lab.get("date")
            or lab.get("test_date")
            or lab.get("collected_date")
            or lab.get("collection_date")
            or lab.get("created_at")
            or "N/A"
        )

        lines.append(
            f"Date: {test_date}"
        )

        # ----------------------------------------------------
        # Additional notes
        # ----------------------------------------------------

        notes = (
            lab.get("notes")
            or lab.get("comment")
            or lab.get("comments")
        )

        if notes:
            lines.append(
                f"Notes: {notes}"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN CHAT ENDPOINT
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse
)
def handle_chat(request: ChatRequest):
    """
    Main healthcare chatbot pipeline.

    Flow:

        User Query
             ↓
        PHI Sanitization
             ↓
        Intent Classification
             ↓
        Patient Context Injection
             ↓
        Appointment Modal if required
             ↓
        Healthcare Tool Execution
             ↓
        Response Formatting
             ↓
        ChatResponse
    """

    # ========================================================
    # 1. SANITIZE QUERY / DETECT PHI
    # ========================================================

    sanitized_q, phi_detected = (
        engine.sanitize_query(
            request.query
        )
    )


    # ========================================================
    # 2. INTENT CLASSIFICATION
    # ========================================================

    classifier_mode = (
        request.classifier_mode
        or "hybrid"
    )

    intent_res = engine.classify(
        request.query,
        mode=classifier_mode
    )


    # ========================================================
    # 3. PRESERVE PHI DETECTION
    # ========================================================

    intent_res.phi_detected = (
        intent_res.phi_detected
        or phi_detected
    )


    # ========================================================
    # 4. INJECT PATIENT ID
    # ========================================================

    if "patient_id" not in intent_res.parameters:

        intent_res.parameters["patient_id"] = (
            request.patient_id
            or "P-1001"
        )


    # ========================================================
    # 5. APPOINTMENT MODAL
    # ========================================================

    action_requires_modal = False
    modal_payload = None

    if intent_res.tool_name == "book_appointment":

        action_requires_modal = True

        extracted_specialty = (
            intent_res.parameters.get(
                "specialty",
                "Cardiology"
            )
        )

        extracted_doctor = (
            intent_res.parameters.get(
                "doctor_name",
                "Dr. Emily Vance"
            )
        )

        extracted_reason = (
            intent_res.parameters.get(
                "reason",
                request.query
            )
        )

        extracted_date = (
            intent_res.parameters.get(
                "preferred_date",
                "2026-08-17"
            )
        )

        extracted_time = (
            intent_res.parameters.get(
                "preferred_time",
                "10:00 AM"
            )
        )

        modal_payload = AppointmentModalPayload(
            specialty=extracted_specialty,
            doctor_name=extracted_doctor,
            reason=extracted_reason,
            preferred_date=extracted_date,
            preferred_time=extracted_time
        )


    # ========================================================
    # 6. EXECUTE HEALTHCARE TOOL
    # ========================================================

    raw_tool_res = tool_registry.execute_tool(
        intent_res.tool_name,
        intent_res.parameters
    )


    # ========================================================
    # 7. CREATE TOOL EXECUTION RESPONSE
    # ========================================================

    tool_exec_res = ToolExecutionResult(
        tool_name=intent_res.tool_name,
        success=raw_tool_res.get(
            "success",
            True
        ),
        data=raw_tool_res,
        message=raw_tool_res.get(
            "message",
            "Tool execution complete."
        )
    )


    # ========================================================
    # 8. DEFAULT RESPONSE
    # ========================================================

    final_text = raw_tool_res.get(
        "message",
        "Request processed successfully."
    )


    # ========================================================
    # 9. RAG RESPONSE
    # ========================================================

    if intent_res.tool_name == "healthcare_rag_qa":

        final_text = raw_tool_res.get(
            "answer",
            final_text
        )


    # ========================================================
    # 10. LAB RESULTS RESPONSE
    # ========================================================

    elif intent_res.tool_name == "get_lab_results":

        patient_id = (
            intent_res.parameters.get(
                "patient_id",
                request.patient_id or "P-1001"
            )
        )

        lab_results = raw_tool_res.get(
            "results",
            []
        )

        final_text = format_lab_results(
            lab_results,
            patient_id
        )


    # ========================================================
    # 11. PRESCRIPTION REFILL RESPONSE
    # ========================================================

    elif intent_res.tool_name == "request_prescription_refill":

        medication = (
            intent_res.parameters.get(
                "medication",
                "Requested medication"
            )
        )

        pharmacy = (
            intent_res.parameters.get(
                "pharmacy",
                "Selected pharmacy"
            )
        )

        final_text = (
            "💊 Prescription Refill Request\n\n"
            f"Medication: {medication}\n"
            f"Pharmacy: {pharmacy}\n\n"
            f"{raw_tool_res.get('message', '')}"
        )


    # ========================================================
    # 12. SUPPORT TICKET RESPONSE
    # ========================================================

    elif intent_res.tool_name == "create_support_ticket":

        final_text = (
            "🎫 Support Ticket\n\n"
            f"{raw_tool_res.get('message', final_text)}"
        )


    # ========================================================
    # 13. SUPPORT TICKET LIST
    # ========================================================

    elif intent_res.tool_name == "list_support_tickets":

        tickets = raw_tool_res.get(
            "tickets",
            []
        )

        if not tickets:

            final_text = (
                "🎫 No open support tickets "
                "were found."
            )

        else:

            lines = [
                "🎫 Your Support Tickets",
                ""
            ]

            for index, ticket in enumerate(
                tickets,
                start=1
            ):

                lines.append(
                    f"Ticket {index}"
                )

                lines.append(
                    f"ID: {ticket.get('ticket_id', 'N/A')}"
                )

                lines.append(
                    f"Subject: {ticket.get('subject', 'N/A')}"
                )

                lines.append(
                    f"Status: {ticket.get('status', 'N/A')}"
                )

                if ticket.get("priority"):
                    lines.append(
                        f"Priority: {ticket.get('priority')}"
                    )

                lines.append("")

            final_text = "\n".join(lines)


    # ========================================================
    # 14. EMERGENCY RESPONSE
    # ========================================================

    elif intent_res.is_emergency:

        final_text = (
            f"🚨 {final_text}\n\n"
            "Immediate Action Recommended: "
            "Call 911 or proceed to the nearest "
            "Emergency Room."
        )


    # ========================================================
    # 15. APPOINTMENT MODAL RESPONSE
    # ========================================================

    elif action_requires_modal:

        final_text = (
            "📅 I have prepared your appointment request.\n\n"
            "Please review the appointment details in "
            "the confirmation pop-up and select your "
            "specialist, health concern, and preferred "
            "time to complete your booking."
        )


    # ========================================================
    # 16. RAG SOURCES
    # ========================================================

    rag_sources = None

    if intent_res.tool_name == "healthcare_rag_qa":

        rag_sources = raw_tool_res.get(
            "sources",
            []
        )


    # ========================================================
    # 17. RETURN FINAL RESPONSE
    # ========================================================

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


# ============================================================
# PATIENT HISTORY
# ============================================================

@app.get("/api/history")
def get_patient_history(
    patient_id: str = Query(
        "P-1001",
        description="Patient ID"
    )
):
    """
    Retrieves patient action history, appointments,
    lab results, prescriptions, and support tickets.
    """

    return tool_registry.get_patient_history(
        patient_id
    )


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

@app.post("/api/appointments/cancel")
def cancel_appointment(
    req: CancelAppointmentRequest
):
    """
    Cancels a scheduled appointment.
    """

    return tool_registry.cancel_appointment(
        req.appointment_id,
        req.patient_id or "P-1001"
    )


# ============================================================
# INTENT COMPARISON
# ============================================================

@app.post(
    "/api/intents/compare",
    response_model=IntentComparisonResult
)
def compare_intent_methods(
    request: ChatRequest
):
    """
    Compares:

        Rule-Based
        LLM-Based
        Hybrid
    """

    rule_res = engine.classify_rule_based(
        request.query
    )

    llm_res = engine.classify_llm_based(
        request.query
    )

    hybrid_res = engine.classify_hybrid(
        request.query
    )

    recommended = "Hybrid Approach"

    if rule_res.is_emergency:

        recommended = (
            "Hybrid "
            "(Rule-Stage Fast Path for Emergency Triage)"
        )

    return IntentComparisonResult(
        query=request.query,
        rule_based=rule_res,
        llm_based=llm_res,
        hybrid=hybrid_res,
        recommended_approach=recommended
    )


# ============================================================
# EVALUATION
# ============================================================

@app.get(
    "/api/evaluate",
    response_model=EvaluationSummary
)
def run_evaluation_benchmark(
    method: str = Query(
        "hybrid",
        description=(
            "Method: "
            "'rule', 'llm', or 'hybrid'"
        )
    )
):
    """
    Runs the evaluation dataset and calculates:

        - Intent accuracy
        - Tool accuracy
        - Average latency
        - Average quality score
        - Category breakdown
    """

    return evaluator.run_evaluation(
        method=method
    )


# ============================================================
# AVAILABLE TOOLS
# ============================================================

@app.get("/api/tools")
def list_registered_tools():
    """
    Lists all available healthcare tools.
    """

    return {
        "tools": [

            {
                "name": "book_appointment",
                "description": (
                    "Schedules a doctor/specialist "
                    "appointment with custom specialist, "
                    "health problem, doctor, and date/time."
                ),
                "parameters": [
                    "specialty",
                    "doctor_name",
                    "preferred_date",
                    "preferred_time",
                    "reason",
                    "patient_id"
                ]
            },

            {
                "name": "cancel_appointment",
                "description": (
                    "Cancels a booked appointment."
                ),
                "parameters": [
                    "appointment_id",
                    "patient_id"
                ]
            },

            {
                "name": "get_lab_results",
                "description": (
                    "Retrieves patient laboratory "
                    "diagnostic reports and blood "
                    "test results."
                ),
                "parameters": [
                    "patient_id",
                    "test_name"
                ]
            },

            {
                "name": "request_prescription_refill",
                "description": (
                    "Processes prescription medication "
                    "refills with doctor approval workflow."
                ),
                "parameters": [
                    "medication",
                    "pharmacy",
                    "patient_id"
                ]
            },

            {
                "name": "triage_emergency_symptoms",
                "description": (
                    "Evaluates medical symptom severity "
                    "for immediate clinical triage."
                ),
                "parameters": [
                    "symptoms",
                    "severity",
                    "patient_id"
                ]
            },

            {
                "name": "create_support_ticket",
                "description": (
                    "Creates a healthcare billing, "
                    "portal tech support, or "
                    "administrative ticket."
                ),
                "parameters": [
                    "category",
                    "subject",
                    "priority",
                    "patient_id"
                ]
            },

            {
                "name": "list_support_tickets",
                "description": (
                    "Lists patient's existing "
                    "support tickets."
                ),
                "parameters": [
                    "patient_id"
                ]
            },

            {
                "name": "healthcare_rag_qa",
                "description": (
                    "Answers medical FAQs, preparation "
                    "rules, and clinic policy queries "
                    "using the healthcare knowledge base."
                ),
                "parameters": [
                    "query"
                ]
            }
        ]
    }


# ============================================================
# DIRECT RAG SEARCH
# ============================================================

@app.get("/api/rag/search")
def search_knowledge_base(
    q: str = Query(
        ...,
        description="Medical search query"
    )
):
    """
    Direct healthcare knowledge-base search.

    Example:

        /api/rag/search?q=How do I prepare for an MRI?
    """

    return tool_registry.rag_engine.generate_rag_answer(
        q
    )
