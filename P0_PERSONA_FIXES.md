# P0 Persona UX Fixes - Implementation Summary

**Date**: March 5, 2026
**Status**: IN PROGRESS

---

## Fix #1: NewGyn® Product Awareness (Sales Rep) ✅

### Issue
Sales reps asking "Does Dermafocus have anything for intimate health / gynecology?" get low retrieval scores (0.375) below evidence threshold (0.50), causing refusal or weak answers.

### Root Cause Analysis
1. ✅ **NewGyn® documents exist and are indexed** (3 docs: factsheet + 2 case studies)
2. ✅ **Retrieval works** - NewGyn doc retrieved as #1 result
3. ❌ **Score too low** - 0.375 < 0.50 evidence threshold
4. ❌ **Query type misclassified** - "Does Dermafocus have...?" classified as "general" (0 boost)

### Fix Implemented (Part 1): Medical Thesaurus Expansion ✅

**File**: `backend/data/medical_thesaurus.json`

**Changes**:
```json
"product_families": {
  "newgyn": ["newgyn", "intimate health", "gynecology", "gynaecology",
             "genitourinary", "vaginal rejuvenation"]
},
"synonyms": {
  "gynecology": ["gynaecology", "intimate health", "vaginal health",
                 "genitourinary", "vulvovaginal"],
  "intimate health": ["gynecology", "vaginal health", "genitourinary",
                      "GSM", "vulvovaginal health"]
},
"product_indications": {
  "intimate health": ["vaginal rejuvenation", "GSM", "genitourinary syndrome",
                      "vaginal atrophy", "vulvovaginal health"],
  "gynecology": ["intimate health", "vaginal rejuvenation", "genitourinary health"]
}
```

**Impact**: Query expansion now includes NewGyn-related terms

---

### Fix Required (Part 2): Product Portfolio Query Type ⏳

**Problem**: "Does Dermafocus have...?" queries need:
1. Lower evidence threshold (0.35 instead of 0.50)
2. Product-specific boosting
3. Portfolio-aware query expansion

**Solution**: Add new query type to query router

**File to Modify**: `backend/app/services/query_router.py`

**Add to QueryType enum** (line ~20):
```python
class QueryType(str, Enum):
    PRODUCT = "product"
    PROTOCOL = "protocol"
    TECHNIQUE = "technique"
    SAFETY = "safety"
    COMPARISON = "comparison"
    MECHANISM = "mechanism"
    CLINICAL_EVIDENCE = "clinical_evidence"
    COST = "cost"
    GENERAL = "general"
    PRODUCT_PORTFOLIO = "product_portfolio"  # NEW
```

**Add classification logic** (line ~75):
```python
# Product portfolio queries (Does X have...? What products...?)
if any(phrase in query_lower for phrase in [
    "does dermafocus have",
    "do you have",
    "what products",
    "product line",
    "product portfolio",
    "anything for"
]):
    return QueryType.PRODUCT_PORTFOLIO
```

**Add retrieval config** (line ~145):
```python
QueryType.PRODUCT_PORTFOLIO: {
    "boost_doc_types": ["factsheet", "brochure"],
    "boost_multiplier": 0.25,
    "prefer_sections": ["overview", "introduction", "indications"],
    "prefer_chunk_types": [],
    "top_k_multiplier": 1.2,
    "evidence_threshold": 0.35  # Lower threshold for existence queries
}
```

**Status**: ⏳ TODO

---

## Fix #2: Language Adaptation (Receptionist) ⏳

### Issue
Receptionist persona receives highly technical responses unsuitable for patient-facing communication.

### Root Cause
- Claude service always uses "physician" audience mode
- No plain-language system prompt variant
- No language adaptation based on user type

### Fix Required

#### Step 1: Add Audience Parameter to Claude Service

**File**: `backend/app/services/claude_service.py`

**Modify __init__** (line ~46):
```python
def __init__(
    self,
    model: str = "claude-3-haiku-20240307",
    audience: str = "physician",  # NEW: "physician" | "non_clinical" | "patient"
    style: str = "clinical"
):
    self.audience = audience
    self.style = style
```

**Add plain-language system prompt** (after line ~332):
```python
def _get_system_prompt_for_audience(self) -> str:
    """Return system prompt based on audience"""

    if self.audience == "non_clinical":
        return """You are a helpful assistant for Dermafocus clinic staff.

Your role is to provide clear, simple explanations about Dermafocus products
and treatments that non-clinical staff (receptionists, coordinators) can use
when communicating with patients.

Guidelines:
- Use plain, everyday language
- Avoid medical jargon unless explaining it
- Focus on practical information (time, aftercare, what to expect)
- Be warm and approachable
- If technical details are needed, explain them simply

For example:
- Instead of "intradermal injection" → "gentle injection into the skin"
- Instead of "polynucleotides" → "natural healing molecules from DNA"
- Instead of "biorevitalization" → "treatment to refresh and renew skin"

Always provide patient-friendly explanations."""

    elif self.audience == "patient":
        return """[Similar but even simpler for direct patient use]"""

    else:  # physician (default)
        return self._build_system_prompt()  # Current clinical prompt
```

#### Step 2: Modify Chat API to Accept Audience

**File**: `backend/app/api/routes/chat.py`

**Add to ChatRequest schema** (line ~115):
```python
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    conversation_id: Optional[str] = None
    history: List[Message] = Field(default_factory=list, max_items=100)
    audience: Optional[str] = Field(default="physician")  # NEW

    @field_validator('audience')
    @classmethod
    def validate_audience(cls, v):
        allowed = ["physician", "non_clinical", "patient"]
        if v not in allowed:
            raise ValueError(f"audience must be one of {allowed}")
        return v
```

**Pass to Claude service** (line ~493):
```python
claude_service = get_claude_service(
    audience=request.audience  # NEW
)
```

**Status**: ⏳ TODO (2 days)

---

## Fix #3: Competitive Positioning (Sales Rep) ⏳

### Issue
Sales reps need to position Plinest® vs competitors, but system refuses comparative queries.

### Current Behavior
Out-of-scope refusal template blocks competitor mentions:
> "I can only provide information about Dermafocus products..."

### Fix Required

**File**: `backend/app/services/claude_service.py`

**Modify refusal logic to check audience** (line ~340):
```python
## OUT-OF-SCOPE REFUSAL TEMPLATES

**IMPORTANT**: Refusal logic depends on audience:

- **physician/non_clinical**: Refuse competitor comparisons (ethical)
- **sales**: Allow competitive positioning (needed for sales)

if audience == "sales":
    # Competitive queries are ALLOWED for sales reps
    # Provide factual differentiation without disparaging competitors
    # Focus on unique features of Dermafocus products
else:
    # Refuse competitor comparisons for clinical users
    "I can only provide information about Dermafocus products..."
```

**Add "sales" audience mode**:
```python
def __init__(
    self,
    model: str = "claude-3-haiku-20240307",
    audience: str = "physician",  # "physician" | "non_clinical" | "patient" | "sales"
    style: str = "clinical"
):
```

**Sales-specific system prompt**:
```python
elif self.audience == "sales":
    return """You are a product knowledge assistant for Dermafocus sales representatives.

Your role is to provide:
- Factual product information and clinical evidence
- Key differentiators vs competitors (when asked)
- Compelling selling points backed by data
- Full product portfolio awareness

Guidelines for competitive positioning:
- Be factual, never disparaging
- Focus on unique Dermafocus features (PN-HPT®, purity, clinical evidence)
- Reference clinical papers when available
- Acknowledge if direct comparison data doesn't exist

Product Portfolio:
- Plinest® (facial biorevitalization)
- Plinest® Eye (periocular)
- Plinest® Hair (alopecia)
- Newest® (advanced skin quality)
- NewGyn® (intimate health)
- Purasomes (colostrum-based)

Be confident, professional, and evidence-based."""
```

**Status**: ⏳ TODO (1 day)

---

## Fix #4: Context Retention (All Personas) ⏳

### Issue
Follow-up questions like "Any clinical papers supporting this?" don't understand "this" refers to previous context.

### Current State
- Redis stores only 3 recent messages (1hr TTL)
- No pronoun resolution
- Follow-up queries classified independently

### Fix Required

**File**: `backend/app/services/conversation_service.py`

**Increase context window** (line ~?):
```python
def get_recent_messages(self, count: int = 10) -> List[Message]:  # Was 3, now 10
```

**Add context analyzer**:
```python
def analyze_followup_context(
    self,
    current_query: str,
    conversation_history: List[Dict[str, str]]
) -> str:
    """
    Enhance current query with context from conversation history.

    Detects pronouns (this, that, it, they) and replaces with
    referenced entities from previous turns.
    """
    if not conversation_history:
        return current_query

    query_lower = current_query.lower()

    # Detect follow-up indicators
    followup_indicators = ["this", "that", "it", "them", "those", "these"]
    is_followup = any(word in query_lower.split() for word in followup_indicators)

    if not is_followup:
        return current_query

    # Extract key entities from last user message
    last_messages = conversation_history[-4:]  # Last 2 turns
    entities = self._extract_entities(last_messages)

    # Construct enhanced query
    if entities:
        enhanced = f"{current_query} (referring to: {', '.join(entities)})"
        return enhanced

    return current_query
```

**Status**: ⏳ TODO (1 day)

---

## Summary of Fixes

| Fix | Priority | Status | Effort | Impact |
|-----|----------|--------|--------|--------|
| NewGyn Thesaurus | P0 | ✅ DONE | 0.5d | Medium |
| Product Portfolio Query Type | P0 | ⏳ TODO | 0.5d | High |
| Language Adaptation | P0 | ⏳ TODO | 2d | High |
| Sales Competitive Mode | P1 | ⏳ TODO | 1d | High |
| Context Retention | P1 | ⏳ TODO | 1d | Medium |

**Total Remaining Effort**: 4.5 days

---

## Testing Plan

### Test 1: NewGyn Awareness (Sales Rep)
```python
Query: "Does Dermafocus have anything for intimate health / gynecology?"
Expected:
- Retrieves NewGyn docs
- Score > 0.50 (with product_portfolio query type)
- Response mentions NewGyn®
```

### Test 2: Plain Language (Receptionist)
```python
Query: "A patient is asking what polynucleotides do for the skin. How should I explain it simply?"
Audience: "non_clinical"
Expected:
- Uses plain language
- Avoids jargon (no "intradermal", "biorevitalization")
- Patient-friendly explanation
```

### Test 3: Competitive Positioning (Sales)
```python
Query: "Give me the top 3 differentiators of Plinest® vs other polynucleotide products"
Audience: "sales"
Expected:
- Provides comparison
- Not refused
- Factual, professional tone
```

### Test 4: Follow-up Context (Clinical)
```python
Q1: "What's the injection technique for Newest® on cheeks?"
Q2: "Any clinical papers supporting this?"
Expected:
- Q2 understands "this" = Newest cheek technique
- Retrieves relevant papers
```

---

**Next Steps**:
1. Implement product_portfolio query type (0.5d)
2. Implement language adaptation (2d)
3. Implement sales mode (1d)
4. Implement context retention (1d)
5. Test all personas comprehensively

---

*Document created: March 5, 2026*
