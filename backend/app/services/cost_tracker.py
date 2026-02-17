"""
Cost Tracking Service
Monitors API costs for Claude, OpenAI, and Pinecone
"""

import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import os

logger = structlog.get_logger()

# API Pricing (as of 2024)
CLAUDE_INPUT_COST_PER_1K = 0.003  # Haiku: $0.003/1K input tokens
CLAUDE_OUTPUT_COST_PER_1K = 0.015  # Haiku: $0.015/1K output tokens
OPENAI_EMBEDDING_COST_PER_1K = 0.00002  # text-embedding-3-small: $0.00002/1K tokens
PINECONE_QUERY_COST = 0.000002  # Serverless: $0.000002 per query


class CostTracker:
    """
    Service for tracking API costs across Claude, OpenAI, and Pinecone
    """

    def __init__(self, cost_log_file: str = "./logs/costs.jsonl"):
        self.cost_log_file = cost_log_file
        self._ensure_log_file()

        # In-memory aggregation (for current session)
        self.session_costs = {
            "claude": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0},
            "openai": {"tokens": 0, "cost": 0.0},
            "pinecone": {"queries": 0, "cost": 0.0},
            "total": 0.0
        }

    def _ensure_log_file(self):
        """Create cost log file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.cost_log_file), exist_ok=True)
        if not os.path.exists(self.cost_log_file):
            with open(self.cost_log_file, 'w') as f:
                pass

    def record_claude_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        request_id: str = None,
        conversation_id: str = None
    ) -> float:
        """
        Record Claude API cost

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            request_id: Optional request ID for tracking
            conversation_id: Optional conversation ID

        Returns:
            Cost in USD
        """
        cost = (
            (input_tokens * CLAUDE_INPUT_COST_PER_1K / 1000) +
            (output_tokens * CLAUDE_OUTPUT_COST_PER_1K / 1000)
        )

        # Update session totals
        self.session_costs["claude"]["input_tokens"] += input_tokens
        self.session_costs["claude"]["output_tokens"] += output_tokens
        self.session_costs["claude"]["cost"] += cost
        self.session_costs["total"] += cost

        # Log to file
        self._log_cost_entry({
            "timestamp": datetime.utcnow().isoformat(),
            "service": "claude",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "request_id": request_id,
            "conversation_id": conversation_id
        })

        logger.info(
            "claude_cost_recorded",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6)
        )

        return cost

    def record_openai_cost(
        self,
        tokens: int,
        request_id: str = None
    ) -> float:
        """
        Record OpenAI embedding cost

        Args:
            tokens: Number of embedding tokens
            request_id: Optional request ID

        Returns:
            Cost in USD
        """
        cost = tokens * OPENAI_EMBEDDING_COST_PER_1K / 1000

        # Update session totals
        self.session_costs["openai"]["tokens"] += tokens
        self.session_costs["openai"]["cost"] += cost
        self.session_costs["total"] += cost

        # Log to file
        self._log_cost_entry({
            "timestamp": datetime.utcnow().isoformat(),
            "service": "openai",
            "tokens": tokens,
            "cost_usd": round(cost, 6),
            "request_id": request_id
        })

        logger.debug(
            "openai_cost_recorded",
            tokens=tokens,
            cost_usd=round(cost, 6)
        )

        return cost

    def record_pinecone_cost(
        self,
        queries: int = 1,
        request_id: str = None
    ) -> float:
        """
        Record Pinecone query cost

        Args:
            queries: Number of queries
            request_id: Optional request ID

        Returns:
            Cost in USD
        """
        cost = queries * PINECONE_QUERY_COST

        # Update session totals
        self.session_costs["pinecone"]["queries"] += queries
        self.session_costs["pinecone"]["cost"] += cost
        self.session_costs["total"] += cost

        # Log to file
        self._log_cost_entry({
            "timestamp": datetime.utcnow().isoformat(),
            "service": "pinecone",
            "queries": queries,
            "cost_usd": round(cost, 6),
            "request_id": request_id
        })

        logger.debug(
            "pinecone_cost_recorded",
            queries=queries,
            cost_usd=round(cost, 6)
        )

        return cost

    def _log_cost_entry(self, entry: Dict[str, Any]):
        """Append cost entry to JSONL log file"""
        try:
            with open(self.cost_log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error("Failed to log cost entry", error=str(e))

    def get_session_costs(self) -> Dict[str, Any]:
        """Get costs for current session"""
        return self.session_costs.copy()

    def get_daily_costs(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get costs for a specific day

        Args:
            date: Date to query (defaults to today)

        Returns:
            Aggregated costs for the day
        """
        if date is None:
            date = datetime.utcnow().date()
        else:
            date = date.date()

        costs = {
            "claude": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0},
            "openai": {"tokens": 0, "cost": 0.0},
            "pinecone": {"queries": 0, "cost": 0.0},
            "total": 0.0,
            "date": date.isoformat()
        }

        try:
            with open(self.cost_log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()

                    if entry_date == date:
                        service = entry["service"]
                        entry_cost = entry["cost_usd"]

                        if service == "claude":
                            costs["claude"]["input_tokens"] += entry.get("input_tokens", 0)
                            costs["claude"]["output_tokens"] += entry.get("output_tokens", 0)
                            costs["claude"]["cost"] += entry_cost
                        elif service == "openai":
                            costs["openai"]["tokens"] += entry.get("tokens", 0)
                            costs["openai"]["cost"] += entry_cost
                        elif service == "pinecone":
                            costs["pinecone"]["queries"] += entry.get("queries", 0)
                            costs["pinecone"]["cost"] += entry_cost

                        costs["total"] += entry_cost

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("Failed to read cost log", error=str(e))

        return costs

    def get_date_range_costs(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get costs for a date range

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Aggregated costs for the date range
        """
        start = start_date.date()
        end = end_date.date()

        costs = {
            "claude": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0},
            "openai": {"tokens": 0, "cost": 0.0},
            "pinecone": {"queries": 0, "cost": 0.0},
            "total": 0.0,
            "start_date": start.isoformat(),
            "end_date": end.isoformat()
        }

        try:
            with open(self.cost_log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()

                    if start <= entry_date <= end:
                        service = entry["service"]
                        entry_cost = entry["cost_usd"]

                        if service == "claude":
                            costs["claude"]["input_tokens"] += entry.get("input_tokens", 0)
                            costs["claude"]["output_tokens"] += entry.get("output_tokens", 0)
                            costs["claude"]["cost"] += entry_cost
                        elif service == "openai":
                            costs["openai"]["tokens"] += entry.get("tokens", 0)
                            costs["openai"]["cost"] += entry_cost
                        elif service == "pinecone":
                            costs["pinecone"]["queries"] += entry.get("queries", 0)
                            costs["pinecone"]["cost"] += entry_cost

                        costs["total"] += entry_cost

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("Failed to read cost log", error=str(e))

        return costs

    def check_daily_threshold(self, threshold_usd: float = 10.0) -> bool:
        """
        Check if today's costs exceed threshold

        Args:
            threshold_usd: Daily cost threshold in USD

        Returns:
            True if threshold exceeded
        """
        daily_costs = self.get_daily_costs()
        exceeded = daily_costs["total"] > threshold_usd

        if exceeded:
            logger.warning(
                "daily_cost_threshold_exceeded",
                threshold_usd=threshold_usd,
                actual_usd=daily_costs["total"]
            )

        return exceeded


# Singleton instance
_cost_tracker = None

def get_cost_tracker() -> CostTracker:
    """Get singleton CostTracker instance"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
