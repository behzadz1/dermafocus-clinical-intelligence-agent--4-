"""
Role-based safety enforcement for chat responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.prompt_customization import AudienceType


PATIENT_REFUSAL_MESSAGE = (
    "I can’t provide treatment protocols, dosing, or injection guidance for patients. "
    "Please consult a licensed clinician for medical advice. "
    "I can share general, non-treatment information if helpful."
)


@dataclass
class RoleSafetyDecision:
    allowed: bool
    reason: str
    response: Optional[str] = None


_DISALLOWED_INTENTS_FOR_PATIENT = {
    "protocol",
    "dosing",
    "equipment",
    "scheduling",
}

_DISALLOWED_KEYWORDS_FOR_PATIENT = (
    "protocol",
    "dose",
    "dosing",
    "ml",
    "mg",
    "needle",
    "gauge",
    "syringe",
    "cannula",
    "injection",
    "inject",
    "intradermal",
    "subdermal",
    "depth",
    "dilution",
    "reconstitution",
    "mixing",
    "session schedule",
    "treatment schedule",
    "technique",
    "vector",
    "steps",
    "how to perform",
)


def _normalize_audience(audience: Optional[str | AudienceType]) -> Optional[str]:
    if isinstance(audience, AudienceType):
        return audience.value
    if isinstance(audience, str):
        return audience.strip().lower()
    return None


def evaluate_role_safety(
    question: str,
    audience: Optional[str | AudienceType],
    intent: Optional[str] = None
) -> RoleSafetyDecision:
    """
    Enforce role-based safety. Patients cannot receive procedural guidance.
    """
    normalized = _normalize_audience(audience)
    if normalized != AudienceType.PATIENT.value:
        return RoleSafetyDecision(allowed=True, reason="audience_allows")

    intent_value = (intent or "").strip().lower()
    if intent_value in _DISALLOWED_INTENTS_FOR_PATIENT:
        return RoleSafetyDecision(
            allowed=False,
            reason=f"patient_disallowed_intent:{intent_value}",
            response=PATIENT_REFUSAL_MESSAGE
        )

    question_lower = (question or "").lower()
    if any(token in question_lower for token in _DISALLOWED_KEYWORDS_FOR_PATIENT):
        return RoleSafetyDecision(
            allowed=False,
            reason="patient_disallowed_topic",
            response=PATIENT_REFUSAL_MESSAGE
        )

    return RoleSafetyDecision(allowed=True, reason="patient_allowed_general")
