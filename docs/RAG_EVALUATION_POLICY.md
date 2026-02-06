# RAG Evaluation Policy

## Scope
This policy governs regression evaluation of the Dermafocus RAG pipeline using the golden QA dataset and the CI quality gate.

## Dataset Versioning
- The dataset is versioned in `backend/tests/fixtures/rag_eval_dataset.json` via a top-level `version` field.
- CI pins the expected version using `--dataset-version` to prevent silent changes.
- Any change to test cases requires bumping the dataset version and updating the pinned value in CI.

## Quality Gate Thresholds
The CI gate fails when any threshold is not met:
- `pass_rate >= 0.90`
- `refusal_accuracy = 1.00`
- `citation_page_valid_rate = 1.00`

## Update Rules
- Dataset changes must include a brief rationale in the PR description.
- New failures must be triaged into retrieval, citation, or refusal error buckets before adjusting thresholds.
- Threshold changes require explicit approval and must be documented here with a rationale.

## Release Criteria
- A passing RAG eval gate is required for release.
- If secrets are unavailable in CI, the release must run the gate in a trusted environment and attach the report.
