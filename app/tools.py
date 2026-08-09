import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from app.rag import HealthcareRAG

class HealthcareToolRegistry:
    def __init__(self, data_path: str = None):
        if data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base_dir, "data", "sample_patients.json")
        
        self.data_path = data_path
        self.rag_engine = HealthcareRAG()
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.db = json.load(f)
        else:
            self.db = {
                "patients": [],
                "lab_results": [],
                "appointments": [],
                "prescriptions": [],
                "tickets": []
            }

    def _save_data(self):
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.db, f, indent=2)
        except Exception:
            pass

    def book_appointment(self, patient_id: str = "P-1001", doctor_name: str = "Dr. Emily Vance", specialty: str = "Cardiology", preferred_date: str = "2026-08-17", preferred_time: str = "10:00 AM", reason: str = "Routine Checkup", patient_name: str = "Sarah Jenkins") -> Dict[str, Any]:
        """Schedules a new medical or specialist appointment."""
        apt_id = f"APT-{uuid.uuid4().hex[:4].upper()}"
        
        date_time_str = f"{preferred_date} {preferred_time}".strip()
        
        appointment = {
            "appointment_id": apt_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "doctor_name": doctor_name if doctor_name else f"Dr. Assigned ({specialty})",
            "specialty": specialty if specialty else "General Medicine",
            "date_time": date_time_str,
            "status": "Confirmed",
            "reason": reason if reason else "Health Consultation",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.db["appointments"].insert(0, appointment)
        self._save_data()

        return {
            "success": True,
            "appointment_id": apt_id,
            "details": appointment,
            "message": f"✅ Appointment Confirmed! Scheduled with {appointment['doctor_name']} ({appointment['specialty']}) for {appointment['date_time']}. Health Concern: '{appointment['reason']}'."
        }

    def cancel_appointment(self, appointment_id: str, patient_id: str = "P-1001") -> Dict[str, Any]:
        """Cancels a scheduled appointment."""
        for apt in self.db["appointments"]:
            if apt["appointment_id"] == appointment_id:
                apt["status"] = "Cancelled"
                self._save_data()
                return {
                    "success": True,
                    "appointment_id": appointment_id,
                    "message": f"Appointment #{appointment_id} with {apt['doctor_name']} has been cancelled."
                }
        return {
            "success": False,
            "message": f"Appointment #{appointment_id} not found."
        }

    def get_lab_results(self, patient_id: str = "P-1001", test_name: str = None) -> Dict[str, Any]:
        """Retrieves patient blood work and laboratory diagnostic reports."""
        patient_labs = [lab for lab in self.db["lab_results"] if lab["patient_id"] == patient_id]
        if not patient_labs:
            patient_labs = [self.db["lab_results"][0]] if self.db["lab_results"] else []
        
        if test_name:
            filtered = [l for l in patient_labs if test_name.lower() in l["test_name"].lower()]
            if filtered:
                patient_labs = filtered

        return {
            "success": True,
            "count": len(patient_labs),
            "results": patient_labs,
            "message": f"Retrieved {len(patient_labs)} lab result records for patient {patient_id}."
        }

    def request_prescription_refill(self, patient_id: str = "P-1001", medication: str = "Atorvastatin", pharmacy: str = "CVS Pharmacy #4821") -> Dict[str, Any]:
        """Processes medication prescription refill requests with doctor approval workflow."""
        meds = [m for m in self.db["prescriptions"] if m["patient_id"] == patient_id]
        matched = None
        for m in meds:
            if medication.lower() in m["medication"].lower():
                matched = m
                break
        
        if not matched and meds:
            matched = meds[0]

        if matched:
            if matched["refills_remaining"] > 0:
                matched["refills_remaining"] -= 1
                self._save_data()
                return {
                    "success": True,
                    "rx_id": matched["rx_id"],
                    "medication": matched["medication"],
                    "pharmacy": pharmacy or matched["pharmacy"],
                    "refills_left": matched["refills_remaining"],
                    "status": "Refill Approved & Sent to Pharmacy",
                    "message": f"Refill order for {matched['medication']} successfully processed and sent to {pharmacy or matched['pharmacy']}. Refills left: {matched['refills_remaining']}."
                }
            else:
                return {
                    "success": False,
                    "rx_id": matched["rx_id"],
                    "medication": matched["medication"],
                    "status": "Doctor Renewal Required",
                    "message": f"No automatic refills remaining for {matched['medication']}. Renewal request submitted to physician."
                }
        
        refill_id = f"RX-{uuid.uuid4().hex[:4].upper()}"
        return {
            "success": True,
            "rx_id": refill_id,
            "medication": medication,
            "pharmacy": pharmacy,
            "status": "Submitted to Pharmacy",
            "message": f"Refill request for '{medication}' submitted to pharmacy {pharmacy}."
        }

    def triage_emergency_symptoms(self, symptoms: str, patient_id: str = "P-1001", severity: str = None) -> Dict[str, Any]:
        """High-priority emergency symptom assessment and triage tool."""
        critical_keywords = ["chest pain", "shortness of breath", "unconscious", "stroke", "paralysis", "head injury", "severe bleeding", "heart attack"]
        is_critical = any(kw in symptoms.lower() for kw in critical_keywords) or severity == "CRITICAL"
        
        if is_critical:
            return {
                "success": True,
                "triage_level": "EMERGENCY_RED",
                "immediate_action": "CALL 911 OR GO TO NEAREST EMERGENCY ROOM IMMEDIATELY",
                "symptoms_evaluated": symptoms,
                "first_aid_guidance": [
                    "Remain calm and sit down immediately.",
                    "Do not attempt to drive yourself to the hospital.",
                    "Call emergency services (911) right away."
                ],
                "message": "🚨 URGENT MEDICAL ALERT: Based on your symptoms, this may be a life-threatening medical emergency. Please call 911 or visit the nearest emergency department right away."
            }
        else:
            return {
                "success": True,
                "triage_level": "NON_EMERGENCY_YELLOW",
                "immediate_action": "Schedule Urgent Care appointment or call Nurse Line",
                "symptoms_evaluated": symptoms,
                "first_aid_guidance": [
                    "Rest and stay hydrated.",
                    "Contact our 24/7 Nurse Line at 1-800-555-NURSE if symptoms worsen."
                ],
                "message": "Symptoms evaluated. We recommend scheduling an urgent care consultation or contacting our 24/7 nurse line if symptoms persist."
            }

    def create_support_ticket(self, category: str = "General Support", subject: str = "Patient Query", patient_id: str = "P-1001", priority: str = "Medium", details: str = "") -> Dict[str, Any]:
        """Creates a healthcare administrative, billing, or tech support ticket."""
        tck_id = f"TCK-{uuid.uuid4().hex[:4].upper()}"
        ticket = {
            "ticket_id": tck_id,
            "patient_id": patient_id,
            "category": category,
            "subject": subject,
            "status": "Open",
            "priority": priority,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "details": details
        }
        self.db["tickets"].insert(0, ticket)
        self._save_data()

        return {
            "success": True,
            "ticket_id": tck_id,
            "ticket": ticket,
            "message": f"Support ticket #{tck_id} created successfully under category '{category}'."
        }

    def list_support_tickets(self, patient_id: str = "P-1001") -> Dict[str, Any]:
        """Fetches existing support and administrative tickets for a patient."""
        tickets = [t for t in self.db["tickets"] if t["patient_id"] == patient_id]
        if not tickets:
            tickets = self.db["tickets"]

        return {
            "success": True,
            "count": len(tickets),
            "tickets": tickets,
            "message": f"Found {len(tickets)} support tickets for patient {patient_id}."
        }

    def healthcare_rag_qa(self, query: str) -> Dict[str, Any]:
        """Queries the healthcare knowledge base using semantic RAG vector retrieval."""
        rag_res = self.rag_engine.generate_rag_answer(query)
        return {
            "success": True,
            "answer": rag_res["answer"],
            "sources": rag_res["sources"],
            "message": f"Retrieved answers from healthcare knowledge base using {len(rag_res['sources'])} source documents."
        }

    def get_patient_history(self, patient_id: str = "P-1001") -> Dict[str, Any]:
        """Returns consolidated activity timeline and medical history for patient."""
        apts = [a for a in self.db.get("appointments", []) if a.get("patient_id") == patient_id]
        labs = [l for l in self.db.get("lab_results", []) if l.get("patient_id") == patient_id]
        rxs = [r for r in self.db.get("prescriptions", []) if r.get("patient_id") == patient_id]
        tickets = [t for t in self.db.get("tickets", []) if t.get("patient_id") == patient_id]

        return {
            "patient_id": patient_id,
            "appointments": apts,
            "lab_results": labs,
            "prescriptions": rxs,
            "tickets": tickets
        }

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool by name with parameter mapping."""
        tool_map = {
            "book_appointment": self.book_appointment,
            "cancel_appointment": self.cancel_appointment,
            "get_lab_results": self.get_lab_results,
            "request_prescription_refill": self.request_prescription_refill,
            "triage_emergency_symptoms": self.triage_emergency_symptoms,
            "create_support_ticket": self.create_support_ticket,
            "list_support_tickets": self.list_support_tickets,
            "healthcare_rag_qa": self.healthcare_rag_qa
        }
        
        fn = tool_map.get(tool_name)
        if not fn:
            return self.healthcare_rag_qa(params.get("query", tool_name))
        
        try:
            import inspect
            sig = inspect.signature(fn)
            valid_args = {k: v for k, v in params.items() if k in sig.parameters}
            return fn(**valid_args)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error executing tool '{tool_name}': {str(e)}"
            }
