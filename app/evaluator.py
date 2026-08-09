import os
import json
import time
from typing import Dict, Any, List
from app.intent_engine import IntentDetectionEngine
from app.tools import HealthcareToolRegistry
from app.models import TestCaseResult, EvaluationSummary

class ChatbotEvaluator:
    def __init__(self, dataset_path: str = None):
        if dataset_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dataset_path = os.path.join(base_dir, "data", "evaluation_dataset.json")
        
        self.dataset_path = dataset_path
        self.engine = IntentDetectionEngine()
        self.tool_registry = HealthcareToolRegistry()
        self.test_cases = self._load_dataset()

    def _load_dataset(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.dataset_path):
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def evaluate_case(self, case: Dict[str, Any], method: str = "hybrid") -> TestCaseResult:
        query = case["query"]
        expected_tool = case["expected_tool"]
        category = case.get("category", "General")
        
        start_t = time.time()
        intent_res = self.engine.classify(query, mode=method)
        
        # Execute tool
        tool_res = self.tool_registry.execute_tool(intent_res.tool_name, intent_res.parameters)
        lat_ms = (time.time() - start_t) * 1000
        
        intent_correct = (intent_res.tool_name == expected_tool)
        tool_correct = (intent_res.tool_name == expected_tool) and tool_res.get("success", False)
        
        # Calculate Response Quality Score (0.0 to 1.0)
        quality = 0.5
        if tool_correct:
            quality += 0.4
        if intent_res.phi_detected and ("REDACTED" in intent_res.reasoning or "create_support_ticket" in intent_res.tool_name or intent_res.phi_detected):
            quality += 0.1 # PHI compliance bonus
        if intent_res.is_emergency and intent_res.tool_name == "triage_emergency_symptoms":
            quality = 1.0 # Perfect safety score
            
        quality = min(1.0, quality)
        
        return TestCaseResult(
            test_id=case["id"],
            category=category,
            query=query,
            expected_tool=expected_tool,
            detected_tool=intent_res.tool_name,
            intent_correct=intent_correct,
            tool_correct=tool_correct,
            latency_ms=round(lat_ms, 2),
            quality_score=round(quality, 2),
            method=method
        )

    def run_evaluation(self, method: str = "hybrid") -> EvaluationSummary:
        results: List[TestCaseResult] = []
        
        for case in self.test_cases:
            res = self.evaluate_case(case, method=method)
            results.append(res)
            
        total = len(results)
        if total == 0:
            return EvaluationSummary(
                total_cases=0, intent_accuracy=0, tool_accuracy=0,
                avg_latency_ms=0, avg_quality_score=0, method=method,
                category_breakdown={}, test_results=[]
            )
            
        intent_acc = sum(1 for r in results if r.intent_correct) / total
        tool_acc = sum(1 for r in results if r.tool_correct) / total
        avg_lat = sum(r.latency_ms for r in results) / total
        avg_qual = sum(r.quality_score for r in results) / total
        
        # Category breakdown
        cat_map: Dict[str, List[TestCaseResult]] = {}
        for r in results:
            cat_map.setdefault(r.category, []).append(r)
            
        cat_breakdown: Dict[str, Dict[str, float]] = {}
        for cat, list_r in cat_map.items():
            n = len(list_r)
            cat_breakdown[cat] = {
                "count": float(n),
                "intent_accuracy": round(sum(1 for x in list_r if x.intent_correct) / n * 100, 1),
                "tool_accuracy": round(sum(1 for x in list_r if x.tool_correct) / n * 100, 1),
                "avg_latency_ms": round(sum(x.latency_ms for x in list_r) / n, 1),
                "avg_quality_score": round(sum(x.quality_score for x in list_r) / n, 2)
            }
            
        return EvaluationSummary(
            total_cases=total,
            intent_accuracy=round(intent_acc * 100, 1),
            tool_accuracy=round(tool_acc * 100, 1),
            avg_latency_ms=round(avg_lat, 2),
            avg_quality_score=round(avg_qual, 2),
            method=method,
            category_breakdown=cat_breakdown,
            test_results=results
        )
