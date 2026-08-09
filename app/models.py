from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., description="User healthcare query or request text")
    patient_id: Optional[str] = Field("P-1001", description="Patient ID for authenticated context")
    classifier_mode: Optional[str] = Field("hybrid", description="Classification approach: 'rule', 'llm', or 'hybrid'")

class IntentResult(BaseModel):
    intent: str
    tool_name: str
    confidence: float
    method_used: str
    parameters: Dict[str, Any] = {}
    reasoning: str
    execution_time_ms: float
    is_emergency: bool = False
    phi_detected: bool = False

class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    data: Any
    message: str

class ModalField(BaseModel):
    key: str
    label: str
    value: Any
    field_type: str = "text"  # text, select, date, textarea
    options: Optional[List[str]] = None

class ActionModalPayload(BaseModel):
    action_type: str  # tool_name
    title: str
    icon: str
    description: str
    fields: List[ModalField]
    """Specific payload for appointment booking modal. Inherits all fields from ActionModalPayload.
    This alias keeps backward compatibility with existing code that expects
    an `AppointmentModalPayload` type.
    """
class AppointmentModalPayload(ActionModalPayload):
    """Payload for appointment booking modal, extending ActionModalPayload with specific fields."""
    # Default values for the generic ActionModalPayload fields
    action_type: str = "book_appointment"
    title: str = "Book Appointment"
    icon: str = "calendar"
    description: str = "Provide details to schedule your appointment."
    fields: List[ModalField] = []

    # Specific appointment fields
    specialty: str
    doctor_name: str
    reason: str
    preferred_date: str
    preferred_time: str




class ChatResponse(BaseModel):
    query: str
    intent_info: IntentResult
    tool_result: ToolExecutionResult
    final_response: str
    sanitized_query: str
    rag_sources: Optional[List[Dict[str, Any]]] = None
    action_requires_modal: bool = True
    modal_payload: Optional[ActionModalPayload] = None

class IntentComparisonResult(BaseModel):
    query: str
    rule_based: IntentResult
    llm_based: IntentResult
    hybrid: IntentResult
    recommended_approach: str

class TestCaseResult(BaseModel):
    test_id: str
    category: str
    query: str
    expected_tool: str
    detected_tool: str
    intent_correct: bool
    tool_correct: bool
    latency_ms: float
    quality_score: float
    method: str

class EvaluationSummary(BaseModel):
    total_cases: int
    intent_accuracy: float
    tool_accuracy: float
    avg_latency_ms: float
    avg_quality_score: float
    method: str
    category_breakdown: Dict[str, Dict[str, float]]
    test_results: List[TestCaseResult]

class CancelAppointmentRequest(BaseModel):
    appointment_id: str
    patient_id: Optional[str] = "P-1001"
