# Fine-Tuning Strategy for DermaFocus Clinical Assistant

## Executive Summary

Fine-tuning can give your model a more authentic "dermatologist voice" and consistent behavior. However, for **knowledge retrieval**, your current RAG approach is superior. The optimal strategy is a **hybrid approach**: RAG for knowledge + fine-tuning for voice/style.

---

## Option 1: Enhanced RAG + Prompt Engineering (Current + Improved)

**Best for:** Most use cases, fastest to implement

### What It Achieves
- ✅ Domain knowledge from your documents
- ✅ Customizable voice through prompting
- ✅ Easy to update (just add documents)
- ✅ No training costs
- ⚠️ Voice consistency depends on prompt quality

### Already Implemented
- Hierarchical chunking
- Hybrid knowledge (documents + Claude's medical training)
- Brand voice customization
- Audience-specific responses

### Enhancement: Few-Shot Examples

Add real examples of ideal responses to your prompts:

```python
FEW_SHOT_EXAMPLES = """
## EXAMPLE INTERACTIONS

### Example 1: Product Question
**User:** What is Newest?
**Ideal Response:**
Newest® is a next-generation bio-remodeling treatment combining Polynucleotides HPT®
with Hyaluronic Acid. Unlike traditional fillers, it works by stimulating fibroblast
activity and promoting natural collagen synthesis.

**Key specifications:**
- Composition: Polynucleotides HPT® + Hyaluronic Acid
- Volume: 2ml per syringe
- Mechanism: Bio-remodeling, not volumizing

[Source: Newest® Factsheet]

---

### Example 2: Protocol Question
**User:** How do I treat hands with Newest?
**Ideal Response:**
## Hand Rejuvenation Protocol: Newest®

**Patient Selection:**
Ideal candidates present with:
- Skin laxity on dorsum of hands
- Crepey texture and fine lines
- Volume loss with visible tendons/veins

**Treatment Schedule:**
| Session | Timing | Purpose |
|---------|--------|---------|
| 1 | Week 0 | Priming |
| 2 | Week 4 | Reinforcement |
| 3 | Week 8 | Consolidation |

**Technique:**
Two approaches available:
1. **Needle technique:** 30G needle, microdroplet in grid pattern
2. **Cannula technique:** 25G 50mm cannula via wrist entry point

**Dosing:** 1ml per hand

⚠️ **Safety:** Superficial subcutaneous plane only. Avoid dorsal venous network.

[Source: Hand Rejuvenation Protocol]

---

### Example 3: Safety Question
**User:** What are the contraindications for Plinest Eye?
**Ideal Response:**
## Plinest® Eye - Contraindications

**Absolute Contraindications:**
- Known hypersensitivity to polynucleotides or any component
- Active infection at treatment site
- Active herpes simplex in treatment area
- Pregnancy and breastfeeding

**Relative Contraindications (Proceed with Caution):**
- Autoimmune conditions
- History of keloid scarring
- Current anticoagulant therapy
- Recent periorbital procedures (<2 weeks)

**Pre-Treatment Assessment:**
Always conduct thorough medical history including:
- Allergies (especially to fish-derived products)
- Current medications
- Previous aesthetic treatments

⚠️ **Important:** When in doubt, defer to physician assessment.

[Source: Plinest® Eye Factsheet, Clinical Guidelines]
"""
```

---

## Option 2: OpenAI Fine-Tuning (GPT-4 / GPT-4o-mini)

**Best for:** Consistent voice, specific output formats, cost optimization

### Advantages
- Self-service, no enterprise contract needed
- Can create highly consistent "dermatologist voice"
- Reduces prompt length (lower per-call costs)
- Better at specific output formats

### Disadvantages
- Training data preparation required
- Ongoing costs for training runs
- Model updates require retraining
- Less capable than Claude for complex reasoning

### Implementation Plan

#### Step 1: Prepare Training Data

Create JSONL file with ideal conversations:

```jsonl
{"messages": [{"role": "system", "content": "You are Dr. DermaAI, a board-certified dermatologist specializing in regenerative aesthetics..."}, {"role": "user", "content": "What needle size for periorbital injections?"}, {"role": "assistant", "content": "For periorbital treatments with Plinest® Eye, I recommend a 30G ½\" needle. The periorbital area has exceptionally thin skin—approximately 0.5mm compared to 2mm elsewhere on the face—which necessitates precise, superficial placement.\n\n**Technical specifications:**\n- Needle: 30G ½\" (0.3mm × 13mm)\n- Depth: Superficial dermis\n- Volume: 0.02ml per injection point\n\n⚠️ **Clinical Pearl:** Always ensure you're above the orbital septum. If you encounter resistance or the patient reports pressure, withdraw slightly.\n\n[Based on Plinest® Eye protocol]"}]}
{"messages": [{"role": "system", "content": "You are Dr. DermaAI..."}, {"role": "user", "content": "Newest vs Plinest - which should I use?"}, {"role": "assistant", "content": "Excellent question—product selection is crucial for optimal outcomes.\n\n## Newest® vs Plinest®: Clinical Decision Guide\n\n| Factor | Newest® | Plinest® |\n|--------|---------|----------|\n| Composition | PN HPT® + HA | PN HPT® only |\n| Primary Action | Hydration + Regeneration | Pure regeneration |\n| Best For | Dehydrated, aging skin | Structural improvement |\n| Areas | Face, neck, hands | Face, specialized areas |\n\n**Choose Newest® when:**\n- Patient presents with dehydration as primary concern\n- Seeking immediate hydration + long-term regeneration\n- Treating hands or décolletage\n\n**Choose Plinest® when:**\n- Targeting specific areas (Plinest® Eye for periorbital)\n- Focus on pure bio-remodeling without HA\n- Patient has adequate hydration\n\n💡 **Pro Tip:** Many practitioners use Newest® as a foundational treatment, then target specific areas with specialized Plinest® variants.\n\n[Based on Dermafocus Product Portfolio]"}]}
```

#### Step 2: Training Data Requirements

| Quality Level | Examples Needed | Expected Results |
|--------------|-----------------|------------------|
| Minimum | 50-100 | Basic style adoption |
| Good | 200-500 | Consistent voice |
| Excellent | 500-1000+ | Near-expert behavior |

#### Step 3: Fine-Tuning Script

```python
# scripts/prepare_finetuning_data.py

import json
from pathlib import Path
from typing import List, Dict

class FineTuningDataPreparer:
    """Prepare training data for OpenAI fine-tuning"""

    SYSTEM_PROMPT = """You are Dr. DermaAI, a board-certified dermatologist and aesthetic medicine specialist
with expertise in Dermafocus regenerative products. You combine deep clinical knowledge with practical
treatment experience.

Your communication style:
- Evidence-based and precise, citing specific products and protocols
- Confident but never dismissive of safety concerns
- Uses proper medical terminology while remaining accessible
- Always includes relevant warnings and contraindications
- Structures responses with clear headers and formatting
- References Dermafocus documentation when applicable

You specialize in:
- Polynucleotide-based treatments (Plinest®, Newest®)
- Bio-remodeling protocols
- Periorbital, perioral, and hand rejuvenation
- Patient selection and safety assessment"""

    def __init__(self, output_path: str = "training_data.jsonl"):
        self.output_path = output_path
        self.conversations = []

    def add_conversation(
        self,
        user_message: str,
        assistant_response: str,
        system_prompt: str = None
    ):
        """Add a training conversation"""
        self.conversations.append({
            "messages": [
                {"role": "system", "content": system_prompt or self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ]
        })

    def add_multi_turn_conversation(
        self,
        turns: List[Dict[str, str]],
        system_prompt: str = None
    ):
        """Add a multi-turn conversation"""
        messages = [{"role": "system", "content": system_prompt or self.SYSTEM_PROMPT}]
        for turn in turns:
            messages.append({"role": turn["role"], "content": turn["content"]})
        self.conversations.append({"messages": messages})

    def export(self):
        """Export to JSONL format"""
        with open(self.output_path, 'w') as f:
            for conv in self.conversations:
                f.write(json.dumps(conv) + '\n')
        print(f"Exported {len(self.conversations)} conversations to {self.output_path}")

    def validate(self) -> Dict:
        """Validate training data"""
        issues = []

        for i, conv in enumerate(self.conversations):
            messages = conv.get("messages", [])

            # Check structure
            if len(messages) < 2:
                issues.append(f"Conversation {i}: Too few messages")

            # Check roles
            roles = [m["role"] for m in messages]
            if roles[0] != "system":
                issues.append(f"Conversation {i}: Should start with system message")

            # Check content length
            for j, msg in enumerate(messages):
                if len(msg["content"]) < 10:
                    issues.append(f"Conversation {i}, message {j}: Content too short")

        return {
            "total_conversations": len(self.conversations),
            "issues": issues,
            "valid": len(issues) == 0
        }


# Example usage
if __name__ == "__main__":
    preparer = FineTuningDataPreparer("dermafocus_training.jsonl")

    # Add example conversations
    preparer.add_conversation(
        user_message="What is the mechanism of action of polynucleotides?",
        assistant_response="""Polynucleotides HPT® work through multiple biological mechanisms:

## Primary Mechanisms

**1. Fibroblast Stimulation**
Polynucleotides bind to purinergic receptors (P2Y) on fibroblasts, triggering:
- Increased collagen type I and III synthesis
- Enhanced elastin production
- Improved extracellular matrix organization

**2. Anti-Inflammatory Action**
- Scavenging of free radicals
- Reduction of oxidative stress markers
- Modulation of inflammatory cytokines

**3. Hydration Enhancement**
- High water-binding capacity
- Improved tissue hydration
- Enhanced nutrient diffusion

## Clinical Translation

These mechanisms translate to:
- Improved skin texture and firmness (2-3 weeks)
- Enhanced elasticity (4-8 weeks)
- Long-term collagen remodeling (up to 6 months)

💡 **Clinical Pearl:** The regenerative effects are cumulative, which is why we recommend a 3-session protocol for optimal results.

[Based on Polynucleotides HPT® mechanism literature]"""
    )

    # Export
    preparer.export()
    print(preparer.validate())
```

#### Step 4: Run Fine-Tuning

```python
# scripts/run_finetuning.py

import openai
from pathlib import Path

def create_fine_tuning_job(
    training_file: str,
    model: str = "gpt-4o-mini-2024-07-18",  # or gpt-4-0613
    suffix: str = "dermafocus"
):
    """Create an OpenAI fine-tuning job"""

    # Upload training file
    with open(training_file, "rb") as f:
        file_response = openai.files.create(
            file=f,
            purpose="fine-tune"
        )

    print(f"Uploaded file: {file_response.id}")

    # Create fine-tuning job
    job = openai.fine_tuning.jobs.create(
        training_file=file_response.id,
        model=model,
        suffix=suffix,
        hyperparameters={
            "n_epochs": 3,
            "batch_size": "auto",
            "learning_rate_multiplier": "auto"
        }
    )

    print(f"Created fine-tuning job: {job.id}")
    return job

def check_job_status(job_id: str):
    """Check fine-tuning job status"""
    job = openai.fine_tuning.jobs.retrieve(job_id)
    print(f"Status: {job.status}")
    print(f"Model: {job.fine_tuned_model}")
    return job

if __name__ == "__main__":
    job = create_fine_tuning_job("dermafocus_training.jsonl")
```

### Cost Estimation (OpenAI)

| Model | Training Cost | Inference Cost |
|-------|---------------|----------------|
| GPT-4o-mini | ~$3 per 1M tokens | $0.15/1M input, $0.60/1M output |
| GPT-4 | ~$25 per 1M tokens | $30/1M input, $60/1M output |

For 500 training examples (~250K tokens): **~$0.75 - $6.25**

---

## Option 3: Open-Source Fine-Tuning (Llama 3, Mistral)

**Best for:** Full control, data privacy, no ongoing API costs

### Advantages
- Complete data privacy (runs locally or your cloud)
- No per-token costs after training
- Full customization control
- Can be deployed on-premises

### Disadvantages
- Requires ML infrastructure
- Lower capability than Claude/GPT-4
- Significant engineering effort
- Ongoing maintenance

### Recommended Models

| Model | Parameters | Quality | Hardware Needed |
|-------|------------|---------|-----------------|
| Llama 3.1 8B | 8B | Good | 1x A100 or 2x RTX 4090 |
| Llama 3.1 70B | 70B | Excellent | 4x A100 |
| Mistral 7B | 7B | Good | 1x A100 or 2x RTX 4090 |
| Mixtral 8x7B | 47B | Very Good | 2x A100 |

### Implementation Outline

```python
# Using Hugging Face + LoRA for efficient fine-tuning

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from datasets import load_dataset

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# Configure LoRA (efficient fine-tuning)
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# Train with your data
trainer = Trainer(
    model=model,
    train_dataset=train_dataset,
    args=TrainingArguments(
        output_dir="./dermafocus-llama",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
    )
)

trainer.train()
```

---

## Option 4: Anthropic Enterprise Fine-Tuning

**Best for:** Keeping Claude quality + custom voice

### How to Access
1. Contact Anthropic sales
2. Enterprise agreement required
3. Minimum commitment varies

### What You Get
- Claude-quality model with your customizations
- Professional support
- Custom deployment options

---

## Recommended Strategy for DermaFocus

### Phase 1: Enhanced RAG (Now - Implemented ✓)
- Hierarchical chunking
- Brand voice customization
- Few-shot examples
- **Cost:** Minimal (API usage only)

### Phase 2: Few-Shot Enhancement (1-2 weeks)
- Create 20-50 gold-standard Q&A pairs
- Add to system prompt
- Test and refine
- **Cost:** Time only

### Phase 3: Evaluate Fine-Tuning Need (After Phase 2)
If you still need:
- More consistent voice → OpenAI fine-tuning
- Lower costs at scale → Open-source fine-tuning
- Best quality → Anthropic enterprise

### Decision Criteria for Phase 3

| If You Need... | Recommendation |
|----------------|----------------|
| Consistent "dermatologist voice" | OpenAI fine-tuning (GPT-4o-mini) |
| Lower per-query costs | Open-source (Llama 3.1) |
| Maximum quality | Stay with Claude + RAG |
| Full data control | Open-source on-premises |
| Enterprise support | Anthropic enterprise |

---

## Training Data Collection Plan

### Sources for Training Examples

1. **Your Existing Documents**
   - Extract Q&A pairs from factsheets
   - Create examples from protocols
   - Use clinical paper summaries

2. **Expert Curation**
   - Have dermatologists write ideal responses
   - Record and transcribe expert consultations
   - Review and edit AI-generated responses

3. **User Interactions**
   - Log real user questions
   - Have experts write ideal answers
   - Use feedback to identify gaps

### Data Format Template

```json
{
  "id": "train_001",
  "category": "product_info",
  "product": "Newest",
  "question": "What is Newest and how does it work?",
  "ideal_response": "Newest® is a regenerative bio-remodeling treatment...",
  "sources": ["Newest Factsheet", "Clinical Overview"],
  "voice_notes": "Confident, educational, includes mechanism",
  "reviewed_by": "Dr. Smith",
  "review_date": "2024-01-15"
}
```

---

## Summary

| Approach | Voice Customization | Knowledge | Cost | Complexity |
|----------|---------------------|-----------|------|------------|
| RAG + Prompting | Good | Excellent | Low | Low |
| RAG + Few-Shot | Very Good | Excellent | Low | Medium |
| OpenAI Fine-Tuning | Excellent | Good | Medium | Medium |
| Open-Source Fine-Tuning | Excellent | Good | High (infra) | High |
| Anthropic Enterprise | Excellent | Excellent | High | Medium |

**Recommendation:** Start with enhanced RAG + few-shot examples. If voice consistency is still insufficient after 2-4 weeks, proceed with OpenAI fine-tuning on GPT-4o-mini.
