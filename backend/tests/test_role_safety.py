from app.policies.role_safety import evaluate_role_safety
from app.services.prompt_customization import AudienceType


def test_patient_blocks_protocol_intent():
    decision = evaluate_role_safety(
        question="What is the protocol for Plinest Eye?",
        audience=AudienceType.PATIENT,
        intent="protocol"
    )
    assert decision.allowed is False


def test_patient_blocks_injection_keywords():
    decision = evaluate_role_safety(
        question="What needle gauge is used for injections?",
        audience="patient",
        intent="equipment"
    )
    assert decision.allowed is False


def test_patient_allows_general_product_info():
    decision = evaluate_role_safety(
        question="What is Newest?",
        audience=AudienceType.PATIENT,
        intent="product_info"
    )
    assert decision.allowed is True
