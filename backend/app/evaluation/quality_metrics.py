"""
Quality Metrics Collection
Tracks retrieval quality, confidence scores, and system performance over time
"""

import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import os
from collections import defaultdict

logger = structlog.get_logger()


class QualityMetricsCollector:
    """
    Service for collecting and analyzing RAG quality metrics
    """

    def __init__(self, metrics_log_file: str = "./logs/quality_metrics.jsonl"):
        self.metrics_log_file = metrics_log_file
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Create metrics log file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.metrics_log_file), exist_ok=True)
        if not os.path.exists(self.metrics_log_file):
            with open(self.metrics_log_file, 'w') as f:
                pass

    def record_query_quality(
        self,
        query: str,
        confidence: float,
        intent: str,
        top_retrieval_score: float,
        num_chunks_retrieved: int,
        num_strong_matches: int,
        evidence_sufficient: bool,
        evidence_reason: Optional[str] = None,
        query_expansion_applied: Optional[str] = None,
        hierarchy_match_type: Optional[str] = None,
        reranking_enabled: bool = False,
        refusal: bool = False,
        conversation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context_relevance: Optional[float] = None,
        groundedness: Optional[float] = None,
        answer_relevance: Optional[float] = None
    ):
        """
        Record quality metrics for a single query

        Args:
            query: User query text (first 100 chars)
            confidence: Final confidence score (0-1)
            intent: Detected query intent
            top_retrieval_score: Highest retrieval score
            num_chunks_retrieved: Number of chunks retrieved
            num_strong_matches: Number of matches above 0.35 threshold
            evidence_sufficient: Whether evidence was sufficient
            evidence_reason: Reason for evidence decision
            query_expansion_applied: Type of query expansion (if any)
            hierarchy_match_type: Type of hierarchy matching
            reranking_enabled: Whether reranking was used
            refusal: Whether request was refused
            conversation_id: Conversation ID
            request_id: Request ID
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_preview": query[:100] if query else "",
            "confidence": round(confidence, 3),
            "intent": intent,
            "top_retrieval_score": round(top_retrieval_score, 3),
            "num_chunks_retrieved": num_chunks_retrieved,
            "num_strong_matches": num_strong_matches,
            "evidence_sufficient": evidence_sufficient,
            "evidence_reason": evidence_reason,
            "query_expansion": query_expansion_applied or "none",
            "hierarchy_match_type": hierarchy_match_type or "unknown",
            "reranking_enabled": reranking_enabled,
            "refusal": refusal,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "context_relevance": round(context_relevance, 3) if context_relevance is not None else None,
            "groundedness": round(groundedness, 3) if groundedness is not None else None,
            "answer_relevance": round(answer_relevance, 3) if answer_relevance is not None else None
        }

        self._log_quality_entry(entry)

        logger.info(
            "quality_metrics_recorded",
            confidence=confidence,
            intent=intent,
            evidence_sufficient=evidence_sufficient,
            refusal=refusal
        )

    def _log_quality_entry(self, entry: Dict[str, Any]):
        """Append quality entry to JSONL log file"""
        try:
            with open(self.metrics_log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error("Failed to log quality entry", error=str(e))

    def get_date_range_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Aggregate quality metrics for a date range

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Aggregated quality metrics
        """
        start = start_date.date()
        end = end_date.date()

        metrics = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_queries": 0,
            "total_refusals": 0,
            "refusal_rate": 0.0,
            "confidence_distribution": {
                "0-20": 0,
                "20-40": 0,
                "40-60": 0,
                "60-80": 0,
                "80-90": 0,
                "90-95": 0,
                "95-100": 0
            },
            "avg_confidence": 0.0,
            "avg_top_retrieval_score": 0.0,
            "avg_chunks_retrieved": 0.0,
            "avg_strong_matches": 0.0,
            "evidence_sufficient_rate": 0.0,
            "intent_distribution": defaultdict(int),
            "query_expansion_distribution": defaultdict(int),
            "hierarchy_match_distribution": defaultdict(int),
            "reranking_usage_rate": 0.0,
            "high_confidence_queries": 0,  # confidence >= 0.9
            "low_confidence_queries": 0    # confidence < 0.6
        }

        total_confidence = 0.0
        total_retrieval_score = 0.0
        total_chunks = 0
        total_strong_matches = 0
        evidence_sufficient_count = 0
        reranking_enabled_count = 0

        # RAG Triad metrics accumulators
        total_context_relevance = 0.0
        total_groundedness = 0.0
        total_answer_relevance = 0.0
        triad_metrics_count = 0

        try:
            with open(self.metrics_log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()

                    if start <= entry_date <= end:
                        metrics["total_queries"] += 1

                        # Refusal tracking
                        if entry.get("refusal", False):
                            metrics["total_refusals"] += 1

                        # Confidence distribution
                        confidence = entry["confidence"]
                        total_confidence += confidence

                        if confidence >= 0.95:
                            metrics["confidence_distribution"]["95-100"] += 1
                            metrics["high_confidence_queries"] += 1
                        elif confidence >= 0.90:
                            metrics["confidence_distribution"]["90-95"] += 1
                            metrics["high_confidence_queries"] += 1
                        elif confidence >= 0.80:
                            metrics["confidence_distribution"]["80-90"] += 1
                        elif confidence >= 0.60:
                            metrics["confidence_distribution"]["60-80"] += 1
                        elif confidence >= 0.40:
                            metrics["confidence_distribution"]["40-60"] += 1
                            metrics["low_confidence_queries"] += 1
                        elif confidence >= 0.20:
                            metrics["confidence_distribution"]["20-40"] += 1
                            metrics["low_confidence_queries"] += 1
                        else:
                            metrics["confidence_distribution"]["0-20"] += 1
                            metrics["low_confidence_queries"] += 1

                        # Retrieval metrics
                        total_retrieval_score += entry.get("top_retrieval_score", 0)
                        total_chunks += entry.get("num_chunks_retrieved", 0)
                        total_strong_matches += entry.get("num_strong_matches", 0)

                        # Evidence sufficiency
                        if entry.get("evidence_sufficient", False):
                            evidence_sufficient_count += 1

                        # Intent distribution
                        intent = entry.get("intent", "unknown")
                        metrics["intent_distribution"][intent] += 1

                        # Query expansion
                        expansion = entry.get("query_expansion", "none")
                        metrics["query_expansion_distribution"][expansion] += 1

                        # Hierarchy matching
                        hierarchy = entry.get("hierarchy_match_type", "unknown")
                        metrics["hierarchy_match_distribution"][hierarchy] += 1

                        # Reranking
                        if entry.get("reranking_enabled", False):
                            reranking_enabled_count += 1

                        # RAG Triad metrics
                        if entry.get("context_relevance") is not None:
                            total_context_relevance += entry.get("context_relevance", 0)
                            total_groundedness += entry.get("groundedness", 0)
                            total_answer_relevance += entry.get("answer_relevance", 0)
                            triad_metrics_count += 1

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("Failed to aggregate quality metrics", error=str(e))

        # Calculate rates and averages
        if metrics["total_queries"] > 0:
            metrics["refusal_rate"] = round(
                metrics["total_refusals"] / metrics["total_queries"], 3
            )
            metrics["avg_confidence"] = round(
                total_confidence / metrics["total_queries"], 3
            )
            metrics["avg_top_retrieval_score"] = round(
                total_retrieval_score / metrics["total_queries"], 3
            )
            metrics["avg_chunks_retrieved"] = round(
                total_chunks / metrics["total_queries"], 1
            )
            metrics["avg_strong_matches"] = round(
                total_strong_matches / metrics["total_queries"], 1
            )
            metrics["evidence_sufficient_rate"] = round(
                evidence_sufficient_count / metrics["total_queries"], 3
            )
            metrics["reranking_usage_rate"] = round(
                reranking_enabled_count / metrics["total_queries"], 3
            )

        # Calculate RAG Triad averages
        if triad_metrics_count > 0:
            metrics["rag_triad"] = {
                "avg_context_relevance": round(total_context_relevance / triad_metrics_count, 3),
                "avg_groundedness": round(total_groundedness / triad_metrics_count, 3),
                "avg_answer_relevance": round(total_answer_relevance / triad_metrics_count, 3),
                "triad_combined_score": round(
                    (total_context_relevance + total_groundedness + total_answer_relevance) / (triad_metrics_count * 3), 3
                ),
                "queries_with_triad_metrics": triad_metrics_count
            }
        else:
            metrics["rag_triad"] = {
                "avg_context_relevance": 0.0,
                "avg_groundedness": 0.0,
                "avg_answer_relevance": 0.0,
                "triad_combined_score": 0.0,
                "queries_with_triad_metrics": 0
            }

        # Convert defaultdicts to regular dicts
        metrics["intent_distribution"] = dict(metrics["intent_distribution"])
        metrics["query_expansion_distribution"] = dict(metrics["query_expansion_distribution"])
        metrics["hierarchy_match_distribution"] = dict(metrics["hierarchy_match_distribution"])

        return metrics

    def get_daily_metrics(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get quality metrics for a specific day"""
        if date is None:
            date = datetime.utcnow()

        start = datetime.combine(date.date(), datetime.min.time())
        end = datetime.combine(date.date(), datetime.max.time())

        return self.get_date_range_metrics(start, end)

    def get_weekly_metrics(self) -> Dict[str, Any]:
        """Get quality metrics for the last 7 days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        return self.get_date_range_metrics(start_date, end_date)

    def get_monthly_metrics(self) -> Dict[str, Any]:
        """Get quality metrics for the last 30 days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        return self.get_date_range_metrics(start_date, end_date)

    def get_quality_trends(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily quality trends for the last N days

        Args:
            days: Number of days to analyze

        Returns:
            List of daily metrics
        """
        trends = []
        end_date = datetime.utcnow()

        for i in range(days):
            date = end_date - timedelta(days=i)
            daily_metrics = self.get_daily_metrics(date)
            trends.append({
                "date": date.date().isoformat(),
                "total_queries": daily_metrics["total_queries"],
                "avg_confidence": daily_metrics["avg_confidence"],
                "refusal_rate": daily_metrics["refusal_rate"],
                "evidence_sufficient_rate": daily_metrics["evidence_sufficient_rate"]
            })

        return list(reversed(trends))

    def identify_low_quality_queries(
        self,
        confidence_threshold: float = 0.6,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Identify queries with low confidence for review

        Args:
            confidence_threshold: Confidence threshold (queries below this are flagged)
            days: Number of days to look back

        Returns:
            List of low-quality query entries
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        start = start_date.date()
        end = end_date.date()

        low_quality_queries = []

        try:
            with open(self.metrics_log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()

                    if start <= entry_date <= end:
                        if entry["confidence"] < confidence_threshold and not entry.get("refusal", False):
                            low_quality_queries.append({
                                "timestamp": entry["timestamp"],
                                "query_preview": entry["query_preview"],
                                "confidence": entry["confidence"],
                                "intent": entry["intent"],
                                "evidence_reason": entry.get("evidence_reason"),
                                "num_strong_matches": entry.get("num_strong_matches", 0)
                            })

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("Failed to identify low quality queries", error=str(e))

        return low_quality_queries


# Singleton instance
_quality_metrics_collector = None

def get_quality_metrics_collector() -> QualityMetricsCollector:
    """Get singleton QualityMetricsCollector instance"""
    global _quality_metrics_collector
    if _quality_metrics_collector is None:
        _quality_metrics_collector = QualityMetricsCollector()
    return _quality_metrics_collector
