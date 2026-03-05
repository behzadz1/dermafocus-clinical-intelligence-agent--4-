# Clinical QA Test Report - DermaAI System
**Date**: March 5, 2026
**Test Suite**: 17 clinical queries across 4 categories
**Overall Score**: **9/17 PASS (52.9%)**

---

## Executive Summary

The DermaAI RAG system demonstrates **strong performance on product knowledge and clinical evidence queries** (Category A & B: 7/10 PASS), but **struggles with edge cases and complex multi-product queries** (Category C & D: 2/7 PASS).

**Key Finding**: The reranker normalization fix (Phase 4.0) is working correctly - all scores are now in 0-1 range, enabling proper evidence thresholds.

---

## Test Results by Category

### Category A: Product Knowledge (5/5 PASS) ✅
**Excellent retrieval quality - system knows the products well**

| Query | Score | Status | Top Doc |
|-------|-------|--------|---------|
| What is Plinest? | 0.989 | ✅ PASS | Polynucleotides vs PRP paper |
| Plinest vs Newest? | 0.754 | ✅ PASS | Newest Factsheet |
| Plinest Eye technique? | 0.988 | ✅ PASS | Periocular PN-HPT paper |
| Newest neck protocol? | 0.990 | ✅ PASS | Neck/Décolletage case study |
| Plinest hair treatment? | 0.950 | ✅ PASS | Alopecia case series |

**Assessment**: Product-specific queries retrieve highly relevant clinical papers and factsheets. Reranker correctly identifies best matches.

---

### Category B: Clinical Depth (4/5 PASS) ✅
**Strong on clinical evidence, weak on safety info**

| Query | Score | Status | Issue |
|-------|-------|--------|-------|
| Needle gauge for décolletage? | 0.898 | ✅ PASS | Found technique details |
| Sessions for perioral? | 0.668 | ⚠️ PARTIAL | Lower confidence |
| **Contraindications?** | **0.336** | **❌ FAIL** | **Critical gap** |
| PN-HPT skin quality evidence? | 0.928 | ✅ PASS | Strong clinical data |
| Dermal priming paradigm? | 0.998 | ✅ PASS | Excellent match |

**Critical Issue**: **Contraindications query failed** (score 0.336) despite query expansion expanding "contraindications" terms. This is a **safety-critical knowledge gap**.

---

### Category C: Edge Cases (0/5 PASS) ❌
**Poor handling of out-of-scope queries - all failed**

| Query | Score | Status | Expected Behavior |
|-------|-------|--------|-------------------|
| Plinest vs Botox? | 0.004 | ❌ FAIL | Should detect out-of-scope (Botox) |
| Rash treatment? | 0.015 | ❌ FAIL | Should refuse medical triage |
| Price of Newest? | 0.009 | ❌ FAIL | Should state pricing not in KB |
| Self-inject at home? | 0.023 | ❌ FAIL | Should warn against unsafe practice |
| Galderma products? | 0.101 | ❌ FAIL | Should detect competitor mention |

**Assessment**: Evidence threshold correctly blocks low-confidence responses, but system needs better guardrail prompts to explain *why* it can't answer (out-of-scope vs. safety vs. missing data).

---

### Category D: Complex Queries (1/2 PASS) ⚠️
**Comparison queries work, treatment planning fails**

| Query | Score | Status | Analysis |
|-------|-------|--------|----------|
| Multi-product treatment plan | 0.134 | ❌ FAIL | Couldn't synthesize across products |
| Plinest vs Newest for hands | 0.821 | ✅ PASS | Comparison boost worked well |

**Assessment**: Comparison query expansion (1.5x top_k, 0.25 boost) successfully retrieves docs for both products. But treatment planning query failed due to poor semantic match.

---

## Top 5 Response Quality Issues

### 1. 🔴 **CRITICAL: Contraindications Knowledge Gap**
**Query**: "What are the contraindications for polynucleotide treatments?"
**Score**: 0.336 (failed evidence threshold)
**Retrieved**: Striae albae paper, HCP brochure (low relevance)

**Root Cause**:
- Contraindications info likely scattered across multiple docs
- Not extracted as dedicated chunks during ingestion
- Query expansion added safety terms but didn't help retrieval

**Impact**: **Safety-critical information missing** - practitioners need this!

**Fix Required**:
- Manual extraction of contraindications from all product docs
- Create dedicated "safety" document type
- Add to factsheets with clear structure
- Boost safety queries more aggressively (current: 0.2, should be 0.3)

---

### 2. ⚠️ **Out-of-Scope Detection Failing**
**All 5 edge case queries**: Retrieved irrelevant docs, low scores correctly blocked evidence

**Problem**: System blocks low-confidence answers but doesn't explain *why*:
- Out-of-scope product (Botox, Galderma)
- Medical triage (rash diagnosis)
- Missing commercial data (pricing)
- Unsafe practice (self-injection)

**Fix Required**:
- Update system prompt to detect and explicitly refuse:
  - Competitor products: "I can only provide information about Dermafocus products..."
  - Medical diagnosis: "Please consult a physician for medical concerns..."
  - Pricing: "Pricing information is not included in my knowledge base..."
  - Safety violations: "Injectable treatments must be administered by qualified practitioners..."

---

### 3. ⚠️ **Treatment Planning Weakness**
**Query**: "45-year-old patient with perioral wrinkles and poor neck skin quality..."
**Score**: 0.134 (failed)

**Retrieved**: Perioral protocol doc (correct area) but missed neck treatment

**Root Cause**: Query mentions TWO treatment areas but retrieval focused on one

**Fix Required**:
- Detect multi-area queries
- Retrieve separately for each area mentioned
- Synthesize treatment plan across results
- Add "combination treatment" examples to knowledge base

---

### 4. ⚠️ **Session Count Query Underperformed**
**Query**: "How many sessions typically needed for Newest perioral?"
**Score**: 0.668 (partial pass)

**Retrieved**: General facial rejuvenation paper (not perioral-specific)

**Issue**: Specific protocol details (session counts) not prominently indexed

**Fix Required**:
- Extract protocol tables as structured data
- Create chunks specifically for dosing/session info
- Boost chunks containing numbers + "sessions" + "weeks"

---

### 5. ℹ️ **Abbreviation Expansion Working Well**
**Query**: "PN-HPT" queries expanded correctly

**Observed**: Medical thesaurus expanded PN→Polynucleotides, HPT→Highly Purified Technology

**Result**: 0.928 score for clinical evidence query (excellent!)

**Validation**: ✅ Phase 4.0 medical thesaurus integration successful

---

## Knowledge Base Gaps

### Missing or Underrepresented Content:

1. **Contraindications & Safety** (CRITICAL)
   - Scattered across docs, not consolidated
   - Need dedicated safety document per product

2. **Treatment Session Details**
   - Number of sessions, intervals, total course duration
   - Not consistently extracted as searchable chunks

3. **Pricing & Commercial Info**
   - Not in knowledge base (expected)
   - Need clear prompt guidance to state this

4. **Combination Treatment Guidance**
   - No docs on multi-product protocols
   - Practitioners often combine treatments

5. **Post-Treatment Care**
   - Limited information on aftercare
   - Important for patient safety

6. **Adverse Events & Management**
   - Minimal coverage
   - Practitioners need this for informed consent

---

## Retrieval Accuracy Analysis

### What's Working Well ✅

1. **Product-Specific Queries**: 5/5 perfect scores (0.75-0.99)
2. **Clinical Evidence Queries**: 2/2 excellent (0.93-0.99)
3. **Comparison Queries**: 1/1 worked (0.82) with query expansion
4. **Reranker Normalization**: All scores 0-1 range, thresholds working
5. **Medical Thesaurus**: PN/HPT expansion improved retrieval

### What Needs Improvement ⚠️

1. **Safety Queries**: Failed contraindications (score 0.34)
2. **Out-of-Scope Handling**: No explicit refusal prompts
3. **Multi-Area Queries**: Missed neck in combined query (0.13)
4. **Numerical Details**: Session counts underperformed (0.67)

---

## Recommendations (Prioritized)

### P0 - Critical (Fix Before Production)

**1. Add Contraindications Data**
- Extract safety info from all product docs
- Create "Product Safety Profiles" document
- Include: contraindications, precautions, drug interactions
- **Impact**: Addresses safety-critical knowledge gap

**2. Enhance System Prompts for Out-of-Scope**
- Add explicit refusal templates:
  - Competitor products
  - Medical diagnosis/triage
  - Pricing/commercial info
  - Unsafe practices
- **Impact**: Better UX, clearer boundaries

### P1 - High Priority

**3. Improve Safety Query Handling**
- Increase safety query boost from 0.2 → 0.3
- Add safety-specific metadata tags
- Create safety query expansion terms
- **Impact**: Better retrieval for contraindications, warnings

**4. Add Treatment Session Protocols**
- Extract tables with session counts, intervals, dosing
- Create structured "protocol cards" per product
- **Impact**: Answers "how many sessions" queries

### P2 - Medium Priority

**5. Multi-Area Query Detection**
- Detect queries mentioning multiple treatment areas
- Retrieve separately for each area
- Synthesize comprehensive treatment plan
- **Impact**: Handles complex clinical scenarios

**6. Add Combination Treatment Guidance**
- Create docs on multi-product protocols
- Common combinations (e.g., Plinest + Newest)
- **Impact**: Supports real-world practitioner workflows

---

## Score Card Summary

| Category | Pass Rate | Grade |
|----------|-----------|-------|
| **Product Knowledge** | 5/5 (100%) | A+ |
| **Clinical Depth** | 4/5 (80%) | B+ |
| **Edge Cases** | 0/5 (0%) | F |
| **Complex Queries** | 1/2 (50%) | C |
| **Overall** | **9/17 (53%)** | **C+** |

---

## Production Readiness Assessment

**Current State**: 53% query success rate

**For Production Launch**:
- ✅ Product knowledge excellent
- ✅ Reranker working correctly
- ✅ Evidence thresholds appropriate
- ❌ **BLOCK: Missing contraindications data**
- ⚠️ Out-of-scope handling needs work
- ⚠️ Complex queries need improvement

**Recommendation**: **Fix P0 issues before launch** (contraindications + refusal prompts), then deploy with monitoring.

**Post-Launch Targets**:
- 70%+ overall pass rate (add P1 fixes)
- 90%+ for product/clinical queries (maintain current)
- 50%+ for edge cases (better refusals)
- 80%+ for complex queries (multi-area handling)

---

## Next Steps

1. **Immediate**: Extract contraindications from existing docs → add to knowledge base
2. **Week 1**: Update system prompts with refusal templates
3. **Week 2**: Increase safety query boost, add session protocol data
4. **Week 3**: Implement multi-area query detection
5. **Month 1**: Add combination treatment guidance docs

---

**Test Date**: March 5, 2026
**RAG Version**: Phase 4.0 (with reranker fix)
**Test Script**: `backend/scripts/clinical_qa_test.py`
**Results**: `backend/scripts/clinical_qa_results.json`
