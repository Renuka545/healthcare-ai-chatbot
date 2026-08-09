#!/usr/bin/env python
"""
Evaluation Runner Script
Evaluates Rule-Based, LLM-Based, and Hybrid Intent Detection approaches on the Healthcare Test Dataset.
"""

import os
import json
import sys
from app.evaluator import ChatbotEvaluator

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def main():
    print_header("HEALTHCARE AI CHATBOT - EVALUATION SUITE BENCHMARK")
    
    evaluator = ChatbotEvaluator()
    print(f"Loaded {len(evaluator.test_cases)} test cases from dataset.")
    
    methods = ["rule", "llm", "hybrid"]
    summaries = {}
    
    for m in methods:
        print(f"\nRunning benchmark for method: '{m.upper()}'...")
        summary = evaluator.run_evaluation(method=m)
        summaries[m] = summary
        
        print(f"\n--- {m.upper()} CLASSIFIER RESULTS ---")
        print(f"Total Test Cases      : {summary.total_cases}")
        print(f"Intent Accuracy       : {summary.intent_accuracy}%")
        print(f"Tool Selection Accuracy: {summary.tool_accuracy}%")
        print(f"Average Latency       : {summary.avg_latency_ms} ms")
        print(f"Average Quality Score : {summary.avg_quality_score} / 1.0")
        
        print("\nCategory Breakdown:")
        print(f"{'Category':<32} | {'Cases':<6} | {'Intent Acc':<10} | {'Tool Acc':<10} | {'Avg Lat (ms)':<12}")
        print("-" * 80)
        for cat, stats in summary.category_breakdown.items():
            print(f"{cat:<32} | {int(stats['count']):<6} | {stats['intent_accuracy']:<9}% | {stats['tool_accuracy']:<9}% | {stats['avg_latency_ms']:<12}")

    print_header("APPROACH COMPARISON SUMMARY")
    print(f"{'Metric / Approach':<25} | {'Rule-Based':<15} | {'LLM-Based':<15} | {'Hybrid (Final)':<15}")
    print("-" * 80)
    print(f"{'Intent Accuracy (%)':<25} | {summaries['rule'].intent_accuracy:<15} | {summaries['llm'].intent_accuracy:<15} | {summaries['hybrid'].intent_accuracy:<15}")
    print(f"{'Tool Accuracy (%)':<25} | {summaries['rule'].tool_accuracy:<15} | {summaries['llm'].tool_accuracy:<15} | {summaries['hybrid'].tool_accuracy:<15}")
    print(f"{'Avg Latency (ms)':<25} | {summaries['rule'].avg_latency_ms:<15} | {summaries['llm'].avg_latency_ms:<15} | {summaries['hybrid'].avg_latency_ms:<15}")
    print(f"{'Response Quality Score':<25} | {summaries['rule'].avg_quality_score:<15} | {summaries['llm'].avg_quality_score:<15} | {summaries['hybrid'].avg_quality_score:<15}")
    print("-" * 80)
    
    # Save evaluation summary to file
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation_results.json")
    out_data = {m: summaries[m].model_dump() for m in methods}
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, indent=2)
        
    print(f"\nFull evaluation report saved to: {out_file}\n")

if __name__ == "__main__":
    main()
