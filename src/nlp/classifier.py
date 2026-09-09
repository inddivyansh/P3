"""
Multi-label Article Classifier (Batched GPU/CPU Pipeline)
=========================================================

High-throughput multi-label classification system using facebook/bart-large-mnli.

Assigns:
    - primary_categories: list of relevant primary categories
    - sub_categories: more granular subcategory labels
    - article_type: dominant primary category

Performance:
    - Uses pipeline batch inference (batch_size=32) for GPU tensor parallelism.
    - Deterministic keyword and hierarchy matching for instant sub-category mapping.
"""

import logging
from typing import Any
import torch

logger = logging.getLogger(__name__)

# ============================================================================
# CATEGORY CONFIGURATION
# ============================================================================

PRIMARY_CATEGORIES = [
    "Defence",
    "Military Affairs",
    "National Security",
    "Geopolitics",
    "International Relations",
    "Foreign Policy",
    "Border Security",
    "Internal Security",
    "Terrorism and Insurgency",
    "Defence Technology",
    "Cybersecurity",
    "Defence Procurement",
    "Military Exercise",
    "Strategic Infrastructure",
    "Maritime Security",
    "Aerospace and Aviation",
    "Space and Defence",
    "Diplomatic Affairs",
    "Strategic Affairs",
]

MULTI_LABEL_THRESHOLD = 0.25
MAX_CATEGORIES = 5
MODEL_NAME = "facebook/bart-large-mnli"

SUB_CATEGORY_MAPPING = {
    "Defence": ["Defence Procurement", "Military Exercise", "Air Defence", "Land Forces", "Defence Infrastructure", "Defence Manufacturing"],
    "Military Affairs": ["Indian Army", "Indian Navy", "Indian Air Force", "Joint Operations", "Military Leadership"],
    "International Relations": ["India-China Relations", "India-Pakistan Relations", "India-US Relations", "Indo-Pacific Strategy"],
    "Geopolitics": ["South Asian Security", "Regional Conflicts", "Territorial Disputes", "Strategic Alliances"],
    "National Security": ["Border Security", "Counterterrorism", "Critical Infrastructure", "Internal Security"],
    "Terrorism and Insurgency": ["Kashmir Security", "Northeast Frontier", "Cross-border Terrorism", "Internal Disturbance"],
    "Defence Technology": ["Missiles", "Fighter Aircraft", "Drones and UAVs", "Naval Vessels", "Radar Systems", "Electronic Warfare"],
    "Cybersecurity": ["Cyber Defence", "Critical Network Security", "Digital Surveillance"],
    "Defence Procurement": ["Capital Acquisition", "Make in India Defence", "Defence Contracts", "Arms Imports"],
    "Maritime Security": ["Indian Ocean Domain", "Coastal Security", "Naval Patrol", "SLOC Protection"],
}


# ============================================================================
# MODEL LOADER
# ============================================================================

_classifier = None


def _load_classifier():
    """Load BART zero-shot classifier lazily."""
    global _classifier

    if _classifier is not None:
        return _classifier

    try:
        from transformers import pipeline as hf_pipeline

        device = 0 if torch.cuda.is_available() else -1
        device_name = "CUDA GPU (FP16)" if device == 0 else "CPU (FP32)"
        logger.info("Loading BART multi-label classifier on %s...", device_name)

        _classifier = hf_pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            device=device,
            torch_dtype=torch.float16 if device == 0 else torch.float32,
        )

        logger.info("Classifier ready.")

    except Exception as e:
        logger.error("Failed to load classifier: %s", e)
        _classifier = None

    return _classifier


# ============================================================================
# SUB-CATEGORY INFERENCE
# ============================================================================

def _infer_sub_categories(text: str, primary_cats: list[str]) -> list[str]:
    """Fast deterministic sub-category matching based on primary categories and keywords."""
    text_lower = text.lower()
    matched = set()

    for prim in primary_cats:
        candidates = SUB_CATEGORY_MAPPING.get(prim, [])
        for cand in candidates:
            cand_words = cand.lower().split()
            # If candidate keyword or phrase appears in text
            if any(w in text_lower for w in cand_words if len(w) > 3):
                matched.add(cand)

    return list(matched)[:4]


# ============================================================================
# BATCH CLASSIFICATION
# ============================================================================

def batch_classify_articles(
    articles: list[dict[str, Any]],
    batch_size: int = 32,
) -> list[dict[str, Any]]:
    """
    Run multi-label classification on a list of articles using parallel batching.
    """
    if not articles:
        return articles

    classifier = _load_classifier()

    if classifier is None:
        logger.warning("Classifier unavailable. Assigning default categories.")
        for a in articles:
            a["primary_categories"] = ["National Security"]
            a["sub_categories"] = []
            a["article_type"] = "National Security"
            a["category"] = "National Security"
            a["category_confidence"] = 0.5
            a["category_scores"] = {"National Security": 0.5}
        return articles

    logger.info(
        "Classifying %d articles in parallel batches (batch_size=%d)...",
        len(articles),
        batch_size,
    )

    texts = []
    for a in articles:
        title = a.get("title", "")
        body = (a.get("article_text") or a.get("summary") or "")[:400]
        text = f"{title}\n{body}".strip() if body else title
        texts.append(text if text else "defence news")

    try:
        results = classifier(
            texts,
            candidate_labels=PRIMARY_CATEGORIES,
            multi_label=True,
            batch_size=batch_size,
        )

        for idx, res in enumerate(results):
            labels = res["labels"]
            scores = res["scores"]

            # Filter by confidence threshold
            qualifying = [
                lbl for lbl, score in zip(labels, scores)
                if score >= MULTI_LABEL_THRESHOLD
            ][:MAX_CATEGORIES]

            if not qualifying:
                qualifying = [labels[0]]

            dominant = labels[0]
            confidence = round(scores[0], 3)
            sub_cats = _infer_sub_categories(texts[idx], qualifying)

            articles[idx]["primary_categories"] = qualifying
            articles[idx]["sub_categories"] = sub_cats
            articles[idx]["article_type"] = dominant
            articles[idx]["category"] = dominant
            articles[idx]["category_confidence"] = confidence
            articles[idx]["category_scores"] = {
                lbl: round(score, 3) for lbl, score in zip(labels[:5], scores[:5])
            }

            if (idx + 1) % 100 == 0 or (idx + 1) == len(articles):
                logger.info("Classification progress: %d/%d completed.", idx + 1, len(articles))

    except Exception as e:
        logger.error("Batch classification error: %s. Using fallback classification.", e)
        for a in articles:
            if "primary_categories" not in a:
                a["primary_categories"] = ["National Security"]
                a["sub_categories"] = []
                a["article_type"] = "National Security"
                a["category"] = "National Security"
                a["category_confidence"] = 0.5
                a["category_scores"] = {"National Security": 0.5}

    logger.info("Multi-label classification complete.")
    return articles


def run_classification(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute the multi-label classification stage."""
    logger.info("======================================================")
    logger.info("Intelligence Platform — Batched Multi-label Classification Stage")
    logger.info("======================================================")

    articles = batch_classify_articles(articles)
    return articles
