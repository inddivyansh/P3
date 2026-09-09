# Implementation Notes

## Phase 0
1. Configure 10–20 curated RSS/Atom feeds.
2. Fetch and normalise feed entries.
3. Extract article text with Trafilatura.
4. Clean and semantically deduplicate articles.
5. Classify using a zero-shot NLI baseline.
6. Store article/prediction data.
7. Build a manually labelled evaluation set.
8. Generate a categorised digest.
9. Measure macro-F1, per-category precision/recall, accuracy and confusion matrix.

## Phase 1
Add Prefect orchestration, human review, PostgreSQL + pgvector, fine-tuned RoBERTa/DistilBERT, and a lightweight dashboard.

## Phase 2
Production hardening, active learning, drift monitoring, multilingual support and dedicated vector infrastructure if required.
