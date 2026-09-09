"""
Defence-Appropriate Sentiment & Stance Analyzer (Batched GPU/CPU)
================================================================

Domain-specific sentiment and stance analysis for defence and national security news:

    Sentiment: Positive | Negative | Neutral | Concern | Critical | Escalatory | De-escalatory | Unclear
    Stance:    Supportive | Critical | Neutral | Alarming | Reassuring | Unclear
    Target:    Government | Military | Organization | Policy | Country | Event | None

Performance:
    - Uses batched BART-large-MNLI zero-shot classification (batch_size=32).
    - Maximizes GPU CUDA tensor parallelism (FP16) or CPU vectorization.
    - Resolves Stance & Target deterministically from classified sentiment & entity metadata.
"""

import logging
from typing import Any
import torch

logger = logging.getLogger(__name__)

# ============================================================================
# LABELS & MAPPINGS
# ============================================================================

SENTIMENT_LABELS = [
    "positive development",
    "negative development",
    "neutral factual reporting",
    "concern or warning",
    "critical of a policy or decision",
    "escalation of tensions or conflict",
    "de-escalation or diplomatic progress",
]

SENTIMENT_LABEL_MAP = {
    "positive development": "Positive",
    "negative development": "Negative",
    "neutral factual reporting": "Neutral",
    "concern or warning": "Concern",
    "critical of a policy or decision": "Critical",
    "escalation of tensions or conflict": "Escalatory",
    "de-escalation or diplomatic progress": "De-escalatory",
}

STANCE_FROM_SENTIMENT = {
    "Positive": "Reassuring",
    "Negative": "Critical",
    "Neutral": "Neutral",
    "Concern": "Alarming",
    "Critical": "Critical",
    "Escalatory": "Alarming",
    "De-escalatory": "Supportive",
    "Unclear": "Neutral",
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
        logger.info("Loading BART zero-shot sentiment classifier on %s...", device_name)

        _classifier = hf_pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=device,
            torch_dtype=torch.float16 if device == 0 else torch.float32,
        )

        logger.info("Sentiment classifier ready.")

    except Exception as e:
        logger.error("Failed to load sentiment classifier: %s", e)
        _classifier = None

    return _classifier


# ============================================================================
# TARGET INFERENCE
# ============================================================================

def _infer_target(article: dict[str, Any]) -> str:
    """Infer target entity category from article metadata and text keywords."""
    title = (article.get("title") or "").lower()
    text = (article.get("summary") or article.get("article_text") or "")[:500].lower()
    combined = f"{title} {text}"

    orgs = article.get("organizations") or []
    equipment = article.get("equipment") or []
    countries = article.get("countries") or []

    if equipment or any(m in combined for m in ["army", "navy", "air force", "iaf", "drdo", "troops", "commanders", "corps"]):
        return "Military"
    if any(g in combined for g in ["government", "ministry", "minister", "parliament", "pib", "cabinet", "pm modi", "rajnath"]):
        return "Government"
    if len(countries) > 0 or any(c in combined for c in ["china", "pakistan", "united states", "russia", "bilateral", "foreign"]):
        return "Country"
    if any(p in combined for p in ["procurement", "policy", "treaty", "deal", "budget", "agreement", "scheme"]):
        return "Policy"
    if any(e in combined for e in ["encounter", "clash", "exercise", "patrol", "blast", "incident", "strike"]):
        return "Event"
    if orgs:
        return "Organization"

    return "Government"


# ============================================================================
# BATCH SENTIMENT ANALYSIS
# ============================================================================

def batch_analyze_sentiment(
    articles: list[dict[str, Any]],
    batch_size: int = 32,
) -> list[dict[str, Any]]:
    """
    Run batched zero-shot sentiment classification.
    Processes 32 articles simultaneously on GPU/CPU for maximum throughput.
    """
    if not articles:
        return articles

    classifier = _load_classifier()

    # If model is unavailable, assign default safe values
    if classifier is None:
        logger.warning("Sentiment classifier not available. Assigning baseline values.")
        for a in articles:
            a["sentiment"] = "Neutral"
            a["stance"] = "Neutral"
            a["sentiment_target"] = _infer_target(a)
        return articles

    logger.info(
        "Analyzing sentiment for %d articles in parallel batches (batch_size=%d)...",
        len(articles),
        batch_size,
    )

    # Prepare batch inputs
    texts = []
    for a in articles:
        title = a.get("title", "")
        body = (a.get("article_text") or a.get("summary") or "")[:400]
        text = f"{title}\n{body}".strip() if body else title
        texts.append(text if text else "news update")

    # Run batched inference through Hugging Face pipeline
    try:
        results = classifier(
            texts,
            candidate_labels=SENTIMENT_LABELS,
            multi_label=False,
            batch_size=batch_size,
        )

        # Apply results to articles
        for idx, res in enumerate(results):
            top_label = res["labels"][0]
            sentiment = SENTIMENT_LABEL_MAP.get(top_label, "Neutral")
            stance = STANCE_FROM_SENTIMENT.get(sentiment, "Neutral")
            target = _infer_target(articles[idx])

            articles[idx]["sentiment"] = sentiment
            articles[idx]["stance"] = stance
            articles[idx]["sentiment_target"] = target

            if (idx + 1) % 100 == 0 or (idx + 1) == len(articles):
                logger.info("Sentiment progress: %d/%d articles completed.", idx + 1, len(articles))

    except Exception as e:
        logger.error("Batched sentiment classification error: %s. Falling back to default labels.", e)
        for a in articles:
            if "sentiment" not in a:
                a["sentiment"] = "Neutral"
                a["stance"] = "Neutral"
                a["sentiment_target"] = _infer_target(a)

    logger.info("Sentiment analysis stage completed successfully.")
    return articles


def run_sentiment_analysis(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute the sentiment analysis stage."""
    logger.info("======================================================")
    logger.info("Intelligence Platform — Batched Sentiment Analysis Stage")
    logger.info("======================================================")

    articles = batch_analyze_sentiment(articles)
    return articles
