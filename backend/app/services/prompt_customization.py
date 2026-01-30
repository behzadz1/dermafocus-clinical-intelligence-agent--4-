"""
Prompt Customization System for DermaFocus Clinical Assistant

Tailors model outputs to align with:
- Brand voice and terminology
- Clinical communication standards
- Response formatting preferences
- Domain-specific knowledge patterns
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field


class AudienceType(Enum):
    """Target audience for response customization"""
    PHYSICIAN = "physician"           # Medical doctors, dermatologists
    NURSE_PRACTITIONER = "nurse_practitioner"  # NPs, PAs
    AESTHETICIAN = "aesthetician"     # Licensed aestheticians
    CLINIC_STAFF = "clinic_staff"     # Front desk, coordinators
    PATIENT = "patient"               # End patients (if enabled)


class ResponseStyle(Enum):
    """Response style preferences"""
    CLINICAL = "clinical"             # Formal, precise medical language
    CONVERSATIONAL = "conversational" # Friendly but professional
    CONCISE = "concise"               # Brief, bullet-point focused
    DETAILED = "detailed"             # Comprehensive explanations
    EDUCATIONAL = "educational"       # Teaching-focused with context


class QueryCategory(Enum):
    """Categories of queries for template matching"""
    PRODUCT_INFO = "product_info"
    TREATMENT_PROTOCOL = "treatment_protocol"
    DOSING_GUIDANCE = "dosing_guidance"
    SAFETY_CONTRAINDICATIONS = "safety_contraindications"
    TECHNIQUE_INSTRUCTION = "technique_instruction"
    COMPARISON = "comparison"
    TROUBLESHOOTING = "troubleshooting"
    PATIENT_SELECTION = "patient_selection"
    AFTERCARE = "aftercare"
    GENERAL_INQUIRY = "general_inquiry"


@dataclass
class BrandVoice:
    """Dermafocus brand voice configuration"""

    # Core brand identity
    brand_name: str = "Dermafocus"
    tagline: str = "Leading the Way in Regenerative Aesthetics"

    # Tone attributes (scale 1-10)
    professionalism: int = 9      # High clinical credibility
    warmth: int = 6               # Approachable but not casual
    confidence: int = 8           # Authoritative without arrogance
    innovation_focus: int = 8     # Emphasize cutting-edge science
    safety_emphasis: int = 10     # Always prioritize safety

    # Language preferences
    use_technical_terms: bool = True
    explain_technical_terms: bool = True
    use_brand_terminology: bool = True

    # Formatting preferences
    use_bullet_points: bool = True
    include_warnings: bool = True
    include_tips: bool = True
    max_paragraph_sentences: int = 3


@dataclass
class DomainTerminology:
    """Dermafocus-specific terminology and preferred terms"""

    # Product names (always use exact branding)
    product_names: Dict[str, str] = field(default_factory=lambda: {
        "newest": "Newest®",
        "plinest": "Plinest®",
        "plinest eye": "Plinest® Eye",
        "plinest hair": "Plinest® Hair",
        "newgyn": "NewGyn®",
        "purasomes": "Purasomes®",
        "purasomes xcell": "Purasomes® XCell",
        "sgc100": "SGC100+",
    })

    # Preferred clinical terms
    preferred_terms: Dict[str, str] = field(default_factory=lambda: {
        # Use these terms instead of alternatives
        "polynucleotides": "Polynucleotides HPT®",
        "ha": "Hyaluronic Acid",
        "hyaluronic acid": "Hyaluronic Acid",
        "pn": "Polynucleotides",
        "injection": "injection",  # not "jab" or "shot"
        "treatment": "treatment",  # not "procedure" for non-invasive
        "session": "treatment session",
        "protocol": "treatment protocol",
        "patient": "patient",  # not "client" in clinical context
        "practitioner": "practitioner",  # inclusive term
        "skin quality": "skin quality",
        "bio-remodeling": "bio-remodeling",
        "regenerative": "regenerative",
    })

    # Terms to avoid
    avoid_terms: List[str] = field(default_factory=lambda: [
        "filler",           # Dermafocus products are not fillers
        "botox",            # Competitor product
        "juvederm",         # Competitor product
        "restylane",        # Competitor product
        "cheap",
        "discount",
        "guarantee results",
        "miracle",
        "cure",
        "permanent",
    ])

    # Anatomical terms (standardized)
    anatomical_terms: Dict[str, str] = field(default_factory=lambda: {
        "periorbital": "periorbital area",
        "perioral": "perioral area",
        "nasolabial": "nasolabial folds",
        "tear trough": "tear trough",
        "marionette": "marionette lines",
        "neck": "neck and décolletage",
        "hands": "dorsum of the hands",
    })


@dataclass
class ResponseTemplates:
    """Templates for different response types"""

    @staticmethod
    def product_info_template() -> str:
        return """
## {product_name}

**Overview**
{overview}

**Composition**
{composition}

**Key Benefits**
{benefits}

**Indications**
{indications}

**Clinical Evidence**
{evidence}

---
*For detailed protocols, ask about "{product_name} treatment protocol"*
"""

    @staticmethod
    def protocol_template() -> str:
        return """
## {protocol_name}

### Patient Selection
{patient_selection}

### Pre-Treatment
{pre_treatment}

### Treatment Protocol

**Session Schedule:**
{session_schedule}

**Technique:**
{technique}

**Dosing:**
{dosing}

### Post-Treatment Care
{aftercare}

### Expected Results
{results}

⚠️ **Safety Considerations**
{safety_notes}
"""

    @staticmethod
    def safety_template() -> str:
        return """
## Safety Information: {topic}

### ⚠️ Contraindications
{contraindications}

### Precautions
{precautions}

### Potential Side Effects
{side_effects}

### When to Refer
{referral_criteria}

---
**Important:** Always conduct a thorough patient assessment before treatment.
"""

    @staticmethod
    def technique_template() -> str:
        return """
## Injection Technique: {area}

### Equipment
{equipment}

### Step-by-Step Technique

{steps}

### Pro Tips
{tips}

### Common Pitfalls to Avoid
{pitfalls}

### Visual Reference
{visual_notes}
"""

    @staticmethod
    def comparison_template() -> str:
        return """
## Comparison: {item1} vs {item2}

| Aspect | {item1} | {item2} |
|--------|---------|---------|
{comparison_rows}

### When to Choose {item1}
{when_item1}

### When to Choose {item2}
{when_item2}

### Can They Be Combined?
{combination_notes}
"""


class OutputCustomizer:
    """
    Customizes model outputs for Dermafocus clinical assistant
    """

    def __init__(
        self,
        audience: AudienceType = AudienceType.PHYSICIAN,
        style: ResponseStyle = ResponseStyle.CLINICAL,
        brand_voice: BrandVoice = None,
        terminology: DomainTerminology = None
    ):
        self.audience = audience
        self.style = style
        self.brand_voice = brand_voice or BrandVoice()
        self.terminology = terminology or DomainTerminology()
        self.templates = ResponseTemplates()

    def build_customization_prompt(self) -> str:
        """
        Build the customization instructions for the system prompt
        """
        prompt_parts = []

        # Brand voice section
        prompt_parts.append(self._build_brand_voice_section())

        # Audience adaptation
        prompt_parts.append(self._build_audience_section())

        # Style preferences
        prompt_parts.append(self._build_style_section())

        # Terminology rules
        prompt_parts.append(self._build_terminology_section())

        # Formatting rules
        prompt_parts.append(self._build_formatting_section())

        return "\n\n".join(prompt_parts)

    def _build_brand_voice_section(self) -> str:
        return f"""## BRAND VOICE: {self.brand_voice.brand_name}

You represent {self.brand_voice.brand_name} - "{self.brand_voice.tagline}"

**Tone Guidelines:**
- Be highly professional and clinically credible
- Maintain a confident, authoritative voice backed by science
- Show warmth and approachability while staying professional
- Emphasize innovation and cutting-edge regenerative technology
- ALWAYS prioritize patient safety above all else

**Brand Personality:**
- Expert but not condescending
- Innovative but evidence-based
- Confident but not overpromising
- Supportive of practitioners' clinical judgment"""

    def _build_audience_section(self) -> str:
        audience_configs = {
            AudienceType.PHYSICIAN: """## AUDIENCE: Medical Professionals (Physicians)

**Communication Style:**
- Use precise medical terminology without excessive explanation
- Reference clinical evidence and mechanisms of action
- Discuss differential considerations and contraindications thoroughly
- Assume advanced anatomical and pharmacological knowledge
- Include specific dosing, depths, and technique details""",

            AudienceType.NURSE_PRACTITIONER: """## AUDIENCE: Nurse Practitioners & Physician Assistants

**Communication Style:**
- Use clinical terminology with brief clarifications when helpful
- Emphasize practical application and protocols
- Include safety checkpoints and documentation reminders
- Reference scope of practice considerations where relevant
- Provide clear step-by-step guidance""",

            AudienceType.AESTHETICIAN: """## AUDIENCE: Licensed Aestheticians

**Communication Style:**
- Explain medical concepts in accessible terms
- Focus on skin assessment and patient consultation
- Emphasize what's within scope vs. requiring physician oversight
- Provide client communication talking points
- Include contraindication screening checklists""",

            AudienceType.CLINIC_STAFF: """## AUDIENCE: Clinic Staff & Coordinators

**Communication Style:**
- Use clear, non-technical language
- Focus on practical information (scheduling, pricing context, patient FAQs)
- Provide scripts for common patient questions
- Emphasize when to escalate to clinical staff
- Include administrative considerations""",

            AudienceType.PATIENT: """## AUDIENCE: Patients (Consumer-Facing)

**Communication Style:**
- Use simple, reassuring language
- Avoid medical jargon or explain it clearly
- Focus on benefits, experience, and what to expect
- Emphasize safety and professional oversight
- Do NOT provide specific medical advice - direct to practitioner"""
        }

        return audience_configs.get(self.audience, audience_configs[AudienceType.PHYSICIAN])

    def _build_style_section(self) -> str:
        style_configs = {
            ResponseStyle.CLINICAL: """## RESPONSE STYLE: Clinical

- Use precise, evidence-based language
- Include relevant clinical parameters (doses, measurements, timeframes)
- Structure information hierarchically (indication → protocol → safety)
- Reference source documents when citing specific claims
- Maintain formal but accessible tone""",

            ResponseStyle.CONVERSATIONAL: """## RESPONSE STYLE: Conversational

- Use a friendly, approachable tone while maintaining professionalism
- Break down complex topics into digestible explanations
- Use analogies where helpful
- Include practical tips and real-world context
- Still maintain clinical accuracy""",

            ResponseStyle.CONCISE: """## RESPONSE STYLE: Concise

- Lead with the direct answer
- Use bullet points for lists
- Limit explanations to essential information
- One concept per paragraph
- Maximum 3-4 sentences per section
- Skip preamble - get straight to the point""",

            ResponseStyle.DETAILED: """## RESPONSE STYLE: Detailed

- Provide comprehensive explanations
- Include mechanism of action and scientific rationale
- Cover edge cases and special considerations
- Add clinical pearls and expert insights
- Include relevant background context""",

            ResponseStyle.EDUCATIONAL: """## RESPONSE STYLE: Educational

- Structure as a teaching moment
- Explain the "why" behind recommendations
- Include relevant anatomy/physiology context
- Provide memory aids and key takeaways
- Suggest further learning resources when appropriate"""
        }

        return style_configs.get(self.style, style_configs[ResponseStyle.CLINICAL])

    def _build_terminology_section(self) -> str:
        # Build product name rules
        product_rules = "\n".join([
            f'- "{k}" → "{v}"'
            for k, v in self.terminology.product_names.items()
        ])

        # Build preferred terms
        preferred = "\n".join([
            f'- Use "{v}" (not informal alternatives)'
            for k, v in list(self.terminology.preferred_terms.items())[:10]
        ])

        # Build avoid list
        avoid = ", ".join(self.terminology.avoid_terms)

        return f"""## TERMINOLOGY RULES

**Product Names (Always Use Exact Branding):**
{product_rules}

**Preferred Clinical Terms:**
{preferred}

**Terms to AVOID:**
{avoid}

**Key Distinctions:**
- Dermafocus products are bio-remodelers/regenerative, NOT fillers
- Use "Polynucleotides HPT®" for the technology, not generic "PN"
- "Treatment session" not "procedure" for non-invasive treatments
- "Practitioner" as inclusive term for all qualified providers"""

    def _build_formatting_section(self) -> str:
        return """## OUTPUT FORMATTING

**Structure:**
- Use headers (##) to organize major sections
- Use bullet points for lists of 3+ items
- Use tables for comparisons
- Keep paragraphs to 2-3 sentences maximum

**Required Elements:**
- ⚠️ Include safety warnings for any protocol or technique discussion
- 💡 Add "Pro Tips" for technique guidance
- 📋 Include "Key Takeaways" for longer responses
- 📚 Cite source documents: [Source: Document Name]

**Visual Hierarchy:**
1. Direct answer to the question
2. Supporting details and context
3. Safety considerations
4. Next steps or follow-up suggestions

**Warnings Format:**
⚠️ **Warning:** [Critical safety information]
⚡ **Caution:** [Important consideration]
💡 **Pro Tip:** [Expert insight]
📋 **Key Takeaway:** [Summary point]"""

    def apply_terminology(self, text: str) -> str:
        """
        Apply terminology corrections to output text
        """
        result = text

        # Apply product name corrections (case-insensitive)
        for informal, formal in self.terminology.product_names.items():
            import re
            pattern = re.compile(re.escape(informal), re.IGNORECASE)
            result = pattern.sub(formal, result)

        return result

    def get_query_template(self, category: QueryCategory) -> str:
        """
        Get the appropriate response template for a query category
        """
        template_map = {
            QueryCategory.PRODUCT_INFO: self.templates.product_info_template(),
            QueryCategory.TREATMENT_PROTOCOL: self.templates.protocol_template(),
            QueryCategory.SAFETY_CONTRAINDICATIONS: self.templates.safety_template(),
            QueryCategory.TECHNIQUE_INSTRUCTION: self.templates.technique_template(),
            QueryCategory.COMPARISON: self.templates.comparison_template(),
        }

        return template_map.get(category, "")

    def classify_query_category(self, query: str) -> QueryCategory:
        """
        Classify the query to determine appropriate template
        """
        query_lower = query.lower()

        category_keywords = {
            QueryCategory.PRODUCT_INFO: ["what is", "composition", "ingredients", "about", "overview"],
            QueryCategory.TREATMENT_PROTOCOL: ["protocol", "how to treat", "treatment plan", "schedule", "sessions"],
            QueryCategory.DOSING_GUIDANCE: ["dose", "dosing", "how much", "quantity", "ml", "amount"],
            QueryCategory.SAFETY_CONTRAINDICATIONS: ["contraindication", "safe", "risk", "side effect", "avoid", "warning"],
            QueryCategory.TECHNIQUE_INSTRUCTION: ["technique", "inject", "needle", "how to", "step by step"],
            QueryCategory.COMPARISON: ["vs", "versus", "compare", "difference", "better", "or"],
            QueryCategory.TROUBLESHOOTING: ["problem", "issue", "not working", "complication", "what if"],
            QueryCategory.PATIENT_SELECTION: ["candidate", "suitable", "patient selection", "who can", "eligibility"],
            QueryCategory.AFTERCARE: ["aftercare", "post treatment", "recovery", "after", "following"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return category

        return QueryCategory.GENERAL_INQUIRY


# Pre-configured customizers for common use cases
CUSTOMIZER_PRESETS = {
    "physician_clinical": OutputCustomizer(
        audience=AudienceType.PHYSICIAN,
        style=ResponseStyle.CLINICAL
    ),
    "physician_concise": OutputCustomizer(
        audience=AudienceType.PHYSICIAN,
        style=ResponseStyle.CONCISE
    ),
    "nurse_practical": OutputCustomizer(
        audience=AudienceType.NURSE_PRACTITIONER,
        style=ResponseStyle.DETAILED
    ),
    "aesthetician_educational": OutputCustomizer(
        audience=AudienceType.AESTHETICIAN,
        style=ResponseStyle.EDUCATIONAL
    ),
    "staff_simple": OutputCustomizer(
        audience=AudienceType.CLINIC_STAFF,
        style=ResponseStyle.CONVERSATIONAL
    ),
}


def get_customizer(preset: str = "physician_clinical") -> OutputCustomizer:
    """Get a pre-configured customizer by preset name"""
    return CUSTOMIZER_PRESETS.get(preset, CUSTOMIZER_PRESETS["physician_clinical"])
