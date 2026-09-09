"""
D-P1-22 — News Feed to Digest Pipeline
=======================================

Zero-shot news article categorisation using Hugging Face
Transformers and facebook/bart-large-mnli.

Features
--------
- NVIDIA CUDA GPU acceleration
- FP16 inference on CUDA
- Batched inference
- Article-by-article classification logging
- Confidence score
- Scores for all categories
- Category distribution
- Compatible JSON output for the existing storage layer
- CPU fallback if CUDA is unavailable
- CUDA out-of-memory handling

Input
-----
data/processed/deduplicated_articles.json

Output
------
data/processed/categorized_articles.json

Run
---
python -m src.categorization.zero_shot
"""

# IMPORTANT:
# from __future__ must appear before normal imports/code.
from __future__ import annotations


# ============================================================
# IMPORTS
# ============================================================

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import torch
from dotenv import load_dotenv
from transformers import pipeline


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "deduplicated_articles.json"
)


OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "categorized_articles.json"
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL_NAME = "facebook/bart-large-mnli"


# ============================================================
# TAXONOMY
# ============================================================

CATEGORIES = [
    "Defence & Security",
    "National Affairs",
    "International Affairs",
    "Economy & Industry",
    "Science & Technology",
    "Society & Public Policy",
    "Sports & Culture",
]


# Keep TAXONOMY as an alias because classifier.py may import it.
TAXONOMY = CATEGORIES


# ============================================================
# GPU CONFIGURATION
# ============================================================

CUDA_AVAILABLE = torch.cuda.is_available()


if CUDA_AVAILABLE:

    DEVICE_NAME = "cuda"

    DEVICE = 0

    TORCH_DTYPE = torch.float16

    logger.info("")
    logger.info("=" * 75)
    logger.info("GPU ACCELERATION ENABLED")
    logger.info("=" * 75)

    logger.info(
        "GPU: %s",
        torch.cuda.get_device_name(0),
    )

    logger.info(
        "PyTorch version: %s",
        torch.__version__,
    )

    logger.info(
        "PyTorch CUDA version: %s",
        torch.version.cuda,
    )

    logger.info(
        "CUDA available: %s",
        torch.cuda.is_available(),
    )

    logger.info(
        "FP16 enabled: YES",
    )

    logger.info("=" * 75)
    logger.info("")

else:

    DEVICE_NAME = "cpu"

    DEVICE = -1

    TORCH_DTYPE = torch.float32

    logger.warning("")
    logger.warning("=" * 75)
    logger.warning("CUDA NOT AVAILABLE")
    logger.warning("Falling back to CPU")
    logger.warning("=" * 75)

    logger.warning(
        "PyTorch version: %s",
        torch.__version__,
    )

    logger.warning(
        "torch.cuda.is_available(): %s",
        torch.cuda.is_available(),
    )

    logger.warning("=" * 75)
    logger.warning("")


# ============================================================
# BATCH SIZE
# ============================================================

# RTX 3050 Laptop GPU:
#
# Start with 2.
#
# If you get CUDA out-of-memory:
#
# Windows CMD:
#     set ZERO_SHOT_BATCH_SIZE=1
#
# Then:
#     python -m src.categorization.zero_shot

BATCH_SIZE = int(
    os.getenv(
        "ZERO_SHOT_BATCH_SIZE",
        "2",
    )
)


# ============================================================
# MODEL INSTANCE
# ============================================================

_classifier = None


def load_classifier():
    """
    Load the BART-MNLI zero-shot classifier.

    The model is loaded only once.

    CUDA:
        device=0
        FP16

    CPU:
        device=-1
        FP32
    """

    global _classifier


    # --------------------------------------------------------
    # Return already-loaded model
    # --------------------------------------------------------

    if _classifier is not None:

        return _classifier


    # --------------------------------------------------------
    # Log model loading
    # --------------------------------------------------------

    logger.info(
        "Loading classifier: %s",
        MODEL_NAME,
    )

    logger.info(
        "Inference device: %s",
        DEVICE_NAME,
    )


    # --------------------------------------------------------
    # CUDA
    # --------------------------------------------------------

    if CUDA_AVAILABLE:

        _classifier = pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            device=0,
            torch_dtype=torch.float16,
        )


    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    else:

        _classifier = pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            device=-1,
        )


    # --------------------------------------------------------
    # Confirmation
    # --------------------------------------------------------

    logger.info(
        "Classifier loaded successfully."
    )


    if CUDA_AVAILABLE:

        logger.info(
            "Model device: %s",
            _classifier.model.device,
        )


    return _classifier


# Keep compatibility with previous code.
get_classifier = load_classifier


# ============================================================
# LOAD ARTICLES
# ============================================================

def load_articles(
    input_path: Path = INPUT_FILE,
) -> list[dict[str, Any]]:
    """
    Load deduplicated articles.

    Supports both:

    1. Wrapped format:

       {
           "articles": [...]
       }

    2. Direct list:

       [...]
    """

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file not found:\n"
            f"{input_path}\n\n"
            f"Run the deduplication stage first."
        )


    # --------------------------------------------------------
    # Read JSON
    # --------------------------------------------------------

    logger.info(
        "Loading articles from: %s",
        input_path,
    )


    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)


    # --------------------------------------------------------
    # Wrapped JSON
    # --------------------------------------------------------

    if isinstance(data, dict):

        articles = data.get(
            "articles",
            [],
        )


    # --------------------------------------------------------
    # Direct list
    # --------------------------------------------------------

    elif isinstance(data, list):

        articles = data


    # --------------------------------------------------------
    # Invalid
    # --------------------------------------------------------

    else:

        raise ValueError(
            "Invalid deduplicated_articles.json format."
        )


    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not isinstance(
        articles,
        list,
    ):

        raise ValueError(
            "'articles' must be a list."
        )


    logger.info(
        "Loaded %d article(s)",
        len(articles),
    )


    return articles


# ============================================================
# BUILD CLASSIFICATION TEXT
# ============================================================

def build_classification_text(
    article: dict[str, Any],
) -> str:
    """
    Build the text passed to BART-MNLI.

    Uses:
        title
        summary
        content

    Article content is capped to control GPU memory.
    """

    title = str(
        article.get("title") or ""
    ).strip()


    summary = str(
        article.get("summary") or ""
    ).strip()


    content = str(
        article.get("content") or ""
    ).strip()


    parts: list[str] = []


    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if title:

        parts.append(
            f"Title: {title}"
        )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    if summary:

        parts.append(
            f"Summary: {summary}"
        )


    # --------------------------------------------------------
    # Content
    # --------------------------------------------------------

    if content:

        # Limit content to prevent unnecessary VRAM use.
        content = content[:4000]

        parts.append(
            f"Content: {content}"
        )


    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    text = "\n".join(
        parts
    ).strip()


    if not text:

        text = "No article text available."


    return text


# ============================================================
# CLASSIFY SINGLE ARTICLE
# ============================================================

def classify_article(
    article: dict[str, Any],
) -> dict[str, Any]:
    """
    Classify a single article.

    Returns original article fields plus:

        category
        confidence
        category_scores
        classifier
        inference_device
    """

    classifier = load_classifier()


    text = build_classification_text(
        article
    )


    # --------------------------------------------------------
    # Model inference
    # --------------------------------------------------------

    try:

        result = classifier(
            text,
            candidate_labels=CATEGORIES,
            multi_label=False,
        )


    except RuntimeError as exc:

        if (
            CUDA_AVAILABLE
            and "out of memory"
            in str(exc).lower()
        ):

            logger.error(
                "CUDA out of memory."
            )

            torch.cuda.empty_cache()

            raise RuntimeError(
                "CUDA out of memory while "
                "classifying an article. "
                "Try ZERO_SHOT_BATCH_SIZE=1."
            ) from exc


        raise


    # --------------------------------------------------------
    # Extract labels/scores
    # --------------------------------------------------------

    labels = result[
        "labels"
    ]

    scores = result[
        "scores"
    ]


    predicted_category = labels[0]

    confidence = float(
        scores[0]
    )


    category_scores = {
        label: float(score)
        for label, score in zip(
            labels,
            scores,
        )
    }


    # --------------------------------------------------------
    # Build result
    # --------------------------------------------------------

    categorized_article = dict(
        article
    )


    categorized_article[
        "category"
    ] = predicted_category


    categorized_article[
        "confidence"
    ] = confidence


    categorized_article[
        "category_scores"
    ] = category_scores


    categorized_article[
        "classifier"
    ] = MODEL_NAME


    categorized_article[
        "inference_device"
    ] = DEVICE_NAME


    return categorized_article


# ============================================================
# CLASSIFY MULTIPLE ARTICLES
# ============================================================

def classify_articles(
    articles: list[dict[str, Any]],
    classifier=None,
) -> list[dict[str, Any]]:
    """
    Classify all articles in batches.

    The optional classifier argument is retained for
    compatibility with the previous project implementation.
    """

    if not articles:

        logger.warning(
            "No articles available for classification."
        )

        return []


    # --------------------------------------------------------
    # Get model
    # --------------------------------------------------------

    if classifier is None:

        classifier = load_classifier()


    # --------------------------------------------------------
    # Prepare texts
    # --------------------------------------------------------

    texts = [
        build_classification_text(
            article
        )
        for article in articles
    ]


    total = len(
        articles
    )


    results: list[
        dict[str, Any]
    ] = []


    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    logger.info("")
    logger.info("=" * 75)
    logger.info(
        "STARTING ARTICLE CATEGORIZATION"
    )
    logger.info("=" * 75)

    logger.info(
        "Total articles: %d",
        total,
    )

    logger.info(
        "Categories: %d",
        len(CATEGORIES),
    )

    logger.info(
        "Batch size: %d",
        BATCH_SIZE,
    )

    logger.info(
        "Model: %s",
        MODEL_NAME,
    )

    logger.info(
        "Device: %s",
        DEVICE_NAME,
    )

    logger.info("=" * 75)
    logger.info("")


    # ========================================================
    # BATCH LOOP
    # ========================================================

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        end = min(
            start + BATCH_SIZE,
            total,
        )


        batch_articles = articles[
            start:end
        ]


        batch_texts = texts[
            start:end
        ]


        # ----------------------------------------------------
        # Inference
        # ----------------------------------------------------

        try:

            batch_results = classifier(
                batch_texts,
                candidate_labels=CATEGORIES,
                multi_label=False,
                batch_size=BATCH_SIZE,
            )


        except RuntimeError as exc:

            # ------------------------------------------------
            # CUDA OOM
            # ------------------------------------------------

            if (
                CUDA_AVAILABLE
                and "out of memory"
                in str(exc).lower()
            ):

                logger.error("")
                logger.error(
                    "CUDA OUT OF MEMORY"
                )

                logger.error(
                    "Failed batch: %d-%d",
                    start + 1,
                    end,
                )


                torch.cuda.empty_cache()


                if BATCH_SIZE > 1:

                    raise RuntimeError(
                        "RTX 3050 ran out of VRAM.\n\n"
                        "Run:\n"
                        "set ZERO_SHOT_BATCH_SIZE=1\n\n"
                        "Then:\n"
                        "python -m "
                        "src.categorization.zero_shot"
                    ) from exc


            raise


        # ----------------------------------------------------
        # Normalize single result
        # ----------------------------------------------------

        if isinstance(
            batch_results,
            dict,
        ):

            batch_results = [
                batch_results
            ]


        # ====================================================
        # ARTICLE RESULTS
        # ====================================================

        for batch_index, (
            article,
            result,
        ) in enumerate(
            zip(
                batch_articles,
                batch_results,
            )
        ):

            labels = result[
                "labels"
            ]

            scores = result[
                "scores"
            ]


            # ------------------------------------------------
            # Prediction
            # ------------------------------------------------

            predicted_category = (
                labels[0]
            )


            confidence = float(
                scores[0]
            )


            # ------------------------------------------------
            # All scores
            # ------------------------------------------------

            category_scores = {
                label: float(score)
                for label, score in zip(
                    labels,
                    scores,
                )
            }


            # ------------------------------------------------
            # Article output
            # ------------------------------------------------

            categorized_article = dict(
                article
            )


            categorized_article[
                "category"
            ] = predicted_category


            categorized_article[
                "confidence"
            ] = confidence


            categorized_article[
                "category_scores"
            ] = category_scores


            categorized_article[
                "classifier"
            ] = MODEL_NAME


            categorized_article[
                "inference_device"
            ] = DEVICE_NAME


            results.append(
                categorized_article
            )


            # ------------------------------------------------
            # Article number
            # ------------------------------------------------

            article_number = (
                start
                + batch_index
                + 1
            )


            # ------------------------------------------------
            # Article title
            # ------------------------------------------------

            title = str(
                article.get(
                    "title",
                    "Untitled",
                )
            ).strip()


            if len(title) > 120:

                title = (
                    title[:117]
                    + "..."
                )


            # =================================================
            # DISPLAY ARTICLE RESULT
            # =================================================

            logger.info(
                "[%d/%d] Article: %s",
                article_number,
                total,
                title,
            )


            logger.info(
                "        Category: %s",
                predicted_category,
            )


            logger.info(
                "        Confidence: %.4f",
                confidence,
            )


            # ------------------------------------------------
            # Top 3 scores
            # ------------------------------------------------

            top_scores = sorted(
                category_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]


            top_score_text = " | ".join(
                f"{label}: {score:.3f}"
                for label, score in top_scores
            )


            logger.info(
                "        Top scores: %s",
                top_score_text,
            )


    # ========================================================
    # FINISHED
    # ========================================================

    logger.info("")
    logger.info("=" * 75)
    logger.info(
        "ARTICLE CATEGORIZATION COMPLETED"
    )
    logger.info("=" * 75)

    logger.info(
        "Successfully categorized: %d/%d",
        len(results),
        total,
    )

    logger.info("=" * 75)
    logger.info("")


    return results


# ============================================================
# CATEGORY DISTRIBUTION
# ============================================================

def get_category_distribution(
    articles: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Count articles in every category.
    """

    counts = {
        category: 0
        for category in CATEGORIES
    }


    for article in articles:

        category = article.get(
            "category"
        )


        if category in counts:

            counts[
                category
            ] += 1


    return counts


# ============================================================
# PRINT CATEGORY STATISTICS
# ============================================================

def print_category_statistics(
    articles: list[dict[str, Any]],
) -> None:
    """
    Print final category distribution.
    """

    counts = (
        get_category_distribution(
            articles
        )
    )


    unclassified = sum(
        1
        for article in articles
        if article.get("category")
        not in CATEGORIES
    )


    logger.info("")
    logger.info(
        "================ CATEGORY DISTRIBUTION ================"
    )


    for category in CATEGORIES:

        logger.info(
            "%-28s %d",
            category,
            counts[category],
        )


    logger.info(
        "%-28s %d",
        "Unclassified",
        unclassified,
    )


    logger.info(
        "========================================================"
    )

    logger.info("")


# ============================================================
# SAVE RESULTS
# ============================================================

def save_articles(
    articles: list[dict[str, Any]],
    output_path: Path = OUTPUT_FILE,
) -> None:
    """
    Save categorized articles.

    IMPORTANT
    ---------
    The storage layer expects the JSON to be wrapped
    inside an object containing an "articles" field.

    Therefore we DO NOT save a raw list here.
    """

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    # --------------------------------------------------------
    # Create compatible payload
    # --------------------------------------------------------

    payload = {
        "article_count": len(
            articles
        ),

        "categories": CATEGORIES,

        "classifier": MODEL_NAME,

        "device": DEVICE_NAME,

        "articles": articles,
    }


    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )


    logger.info(
        "Saved categorised articles to: %s",
        output_path,
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_categorization() -> list[dict[str, Any]]:
    """
    Execute the complete zero-shot categorisation stage.
    """

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    logger.info("")
    logger.info(
        "========================================================"
    )

    logger.info(
        "D-P1-22 — Zero-Shot News Categorisation"
    )

    logger.info(
        "========================================================"
    )


    # --------------------------------------------------------
    # Load input
    # --------------------------------------------------------

    articles = load_articles()


    if not articles:

        logger.warning(
            "No articles available for categorisation."
        )


        save_articles([])


        return []


    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    classifier = load_classifier()


    # --------------------------------------------------------
    # Categorize
    # --------------------------------------------------------

    categorized_articles = (
        classify_articles(
            articles,
            classifier,
        )
    )


    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    print_category_statistics(
        categorized_articles
    )


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_articles(
        categorized_articles
    )


    # --------------------------------------------------------
    # Final message
    # --------------------------------------------------------

    logger.info(
        "Categorisation completed successfully."
    )


    return categorized_articles


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":

    try:

        run_categorization()

    except KeyboardInterrupt:

        logger.warning(
            "Categorisation interrupted by user."
        )

        sys.exit(1)

    except Exception as exc:

        logger.exception(
            "Categorisation failed: %s",
            exc,
        )

        sys.exit(1)