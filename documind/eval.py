from __future__ import annotations

from typing import Any, Dict, List


def evaluate_extraction(results: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Very lightweight evaluation utility that mirrors the project specification."""
    total = len(ground_truth)
    correct = 0
    for item in ground_truth:
        for result in results:
            if result.get("field_name") == item.get("field_name") and result.get("value") == item.get("value"):
                correct += 1
                break

    accuracy = (correct / total) if total else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "total_fields": total,
        "correct_fields": correct,
        "status": "ok",
    }
