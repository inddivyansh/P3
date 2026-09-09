"""Macro-F1, precision, recall, accuracy and confusion-matrix evaluation."""
"""
D-P1-22 — News Feed to Digest Pipeline

Categorisation evaluation module.

Purpose:
    Measure the quality of the news categorisation system against
    human-verified gold labels.

Primary metric:
    Macro-F1

Additional metrics:
    - Accuracy
    - Per-category precision
    - Per-category recall
    - Per-category F1
    - Confusion matrix

Evaluation workflow:

    Categorized articles
            ↓
       Sample articles
            ↓
      Human gold labels
            ↓
       Model predictions
            ↓
       Evaluation metrics
            ↓
      Error analysis

The gold-standard labels must NOT be used for training the model
being evaluated.
"""

import csv
import json
import logging
import random
from pathlib import Path
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "categorized_articles.json"
)

EVALUATION_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "evaluation"
)

SAMPLE_FILE = (
    EVALUATION_DIR
    / "evaluation_sample.csv"
)

RESULTS_FILE = (
    EVALUATION_DIR
    / "evaluation_results.json"
)

CONFUSION_MATRIX_FILE = (
    EVALUATION_DIR
    / "confusion_matrix.csv"
)


# ============================================================================
# TAXONOMY
# ============================================================================

CATEGORIES = [
    "Defence & Security",
    "National Affairs",
    "International Affairs",
    "Economy & Industry",
    "Science & Technology",
    "Society & Public Policy",
    "Sports & Culture",
]


# ============================================================================
# CONFIGURATION
# ============================================================================

# Target evaluation-set size.
DEFAULT_SAMPLE_SIZE = 200

# Reproducible random sampling.
RANDOM_SEED = 42


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================================
# LOAD ARTICLES
# ============================================================================

def load_articles(
    input_path: Path = INPUT_FILE,
) -> list[dict[str, Any]]:
    """Load categorised articles."""

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run zero_shot.py first."
        )

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    articles = data.get(
        "articles",
        [],
    )

    if not isinstance(
        articles,
        list,
    ):

        raise ValueError(
            "Invalid categorized_articles.json format."
        )

    return articles


# ============================================================================
# REPRESENTATIVE ARTICLES
# ============================================================================

def get_representative_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Return one representative article per story cluster.

    This avoids evaluating the same underlying story multiple times
    simply because several news sources reported it.
    """

    representatives = [
        article
        for article in articles
        if article.get(
            "is_cluster_representative",
            True,
        )
    ]

    logger.info(
        "Representative stories available: %d",
        len(representatives),
    )

    return representatives


# ============================================================================
# SAMPLING
# ============================================================================

def create_evaluation_sample(
    articles: list[dict[str, Any]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> list[dict[str, Any]]:
    """
    Create a random evaluation sample.

    The sample is intentionally independent of the model's confidence
    so that the evaluation does not only test easy articles.
    """

    if not articles:

        return []

    actual_size = min(
        sample_size,
        len(articles),
    )

    random.seed(
        RANDOM_SEED
    )

    sample = random.sample(
        articles,
        actual_size,
    )

    return sample


# ============================================================================
# CREATE LABELING FILE
# ============================================================================

def create_labeling_file(
    articles: list[dict[str, Any]],
    output_path: Path = SAMPLE_FILE,
) -> None:
    """
    Create a CSV file for manual annotation.

    The 'gold_category' column is intentionally empty.

    You will fill this column manually with the correct category.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "article_id",
        "story_cluster_id",
        "title",
        "source",
        "url",
        "predicted_category",
        "model_confidence",
        "article_text",
        "gold_category",
        "annotation_notes",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for article in articles:

            writer.writerow(
                {
                    "article_id": article.get(
                        "article_id",
                        "",
                    ),
                    "story_cluster_id": article.get(
                        "story_cluster_id",
                        "",
                    ),
                    "title": article.get(
                        "title",
                        "",
                    ),
                    "source": article.get(
                        "source",
                        "",
                    ),
                    "url": article.get(
                        "url",
                        "",
                    ),
                    "predicted_category": article.get(
                        "category",
                        "",
                    ),
                    "model_confidence": article.get(
                        "category_confidence",
                        "",
                    ),
                    "article_text": article.get(
                        "article_text",
                        "",
                    ),
                    "gold_category": "",
                    "annotation_notes": "",
                }
            )

    logger.info(
        "Evaluation labeling file created:"
    )

    logger.info(
        "%s",
        output_path,
    )


# ============================================================================
# LOAD GOLD LABELS
# ============================================================================

def load_gold_labels(
    input_path: Path = SAMPLE_FILE,
) -> list[dict[str, Any]]:
    """
    Load manually labelled evaluation data.

    Only rows with a valid gold_category are evaluated.
    """

    if not input_path.exists():

        raise FileNotFoundError(
            f"Evaluation file not found: {input_path}\n"
            "Run the evaluation setup first."
        )

    with input_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        reader = csv.DictReader(
            file
        )

        rows = list(reader)

    valid_rows = []

    for row in rows:

        gold_category = (
            row.get(
                "gold_category",
                "",
            )
            or ""
        ).strip()

        predicted_category = (
            row.get(
                "predicted_category",
                "",
            )
            or ""
        ).strip()

        if not gold_category:

            continue

        if gold_category not in CATEGORIES:

            logger.warning(
                "Ignoring invalid category: %s",
                gold_category,
            )

            continue

        if predicted_category not in CATEGORIES:

            logger.warning(
                "Ignoring row with invalid prediction: %s",
                predicted_category,
            )

            continue

        valid_rows.append(
            row
        )

    logger.info(
        "Loaded %d manually labelled article(s).",
        len(valid_rows),
    )

    return valid_rows


# ============================================================================
# METRICS
# ============================================================================

def calculate_metrics(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate categorisation metrics.
    """

    if not rows:

        raise ValueError(
            "No valid labelled rows available."
        )

    y_true = [
        row["gold_category"]
        for row in rows
    ]

    y_pred = [
        row["predicted_category"]
        for row in rows
    ]

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    precision = precision_score(
        y_true,
        y_pred,
        labels=CATEGORIES,
        average="macro",
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        y_pred,
        labels=CATEGORIES,
        average="macro",
        zero_division=0,
    )

    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=CATEGORIES,
        average="macro",
        zero_division=0,
    )

    weighted_f1 = f1_score(
        y_true,
        y_pred,
        labels=CATEGORIES,
        average="weighted",
        zero_division=0,
    )

    report = classification_report(
        y_true,
        y_pred,
        labels=CATEGORIES,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=CATEGORIES,
    )

    return {
        "sample_size": len(rows),
        "accuracy": round(
            float(accuracy),
            4,
        ),
        "macro_precision": round(
            float(precision),
            4,
        ),
        "macro_recall": round(
            float(recall),
            4,
        ),
        "macro_f1": round(
            float(macro_f1),
            4,
        ),
        "weighted_f1": round(
            float(weighted_f1),
            4,
        ),
        "per_category": {
            category: {
                "precision": round(
                    float(
                        report[
                            category
                        ][
                            "precision"
                        ]
                    ),
                    4,
                ),
                "recall": round(
                    float(
                        report[
                            category
                        ][
                            "recall"
                        ]
                    ),
                    4,
                ),
                "f1": round(
                    float(
                        report[
                            category
                        ][
                            "f1"
                        ]
                    ),
                    4,
                ),
                "support": int(
                    report[
                        category
                    ][
                        "support"
                    ]
                ),
            }
            for category in CATEGORIES
        },
        "confusion_matrix": matrix.tolist(),
    }


# ============================================================================
# SAVE RESULTS
# ============================================================================

def save_results(
    results: dict[str, Any],
    output_path: Path = RESULTS_FILE,
) -> None:
    """Save evaluation metrics as JSON."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    logger.info(
        "Evaluation results saved to: %s",
        output_path,
    )


# ============================================================================
# SAVE CONFUSION MATRIX
# ============================================================================

def save_confusion_matrix(
    results: dict[str, Any],
    output_path: Path = CONFUSION_MATRIX_FILE,
) -> None:
    """Save the confusion matrix as CSV."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    matrix = results[
        "confusion_matrix"
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "Actual / Predicted"
            ]
            + CATEGORIES
        )

        for category, row in zip(
            CATEGORIES,
            matrix,
        ):

            writer.writerow(
                [category]
                + row
            )

    logger.info(
        "Confusion matrix saved to: %s",
        output_path,
    )


# ============================================================================
# PRINT RESULTS
# ============================================================================

def print_results(
    results: dict[str, Any],
) -> None:
    """Print evaluation results."""

    logger.info("")
    logger.info(
        "========================================================"
    )

    logger.info(
        "D-P1-22 — CATEGORISATION EVALUATION"
    )

    logger.info(
        "========================================================"
    )

    logger.info(
        "Evaluation sample: %d",
        results["sample_size"],
    )

    logger.info(
        "Accuracy:           %.2f%%",
        results["accuracy"] * 100,
    )

    logger.info(
        "Macro Precision:    %.4f",
        results["macro_precision"],
    )

    logger.info(
        "Macro Recall:       %.4f",
        results["macro_recall"],
    )

    logger.info(
        "Macro-F1:            %.4f",
        results["macro_f1"],
    )

    logger.info(
        "Weighted-F1:         %.4f",
        results["weighted_f1"],
    )

    logger.info("")
    logger.info(
        "Per-category results:"
    )

    for category in CATEGORIES:

        metrics = results[
            "per_category"
        ][category]

        logger.info(
            "%-28s "
            "P=%.3f "
            "R=%.3f "
            "F1=%.3f "
            "N=%d",
            category,
            metrics["precision"],
            metrics["recall"],
            metrics["f1"],
            metrics["support"],
        )

    logger.info(
        "========================================================"
    )


# ============================================================================
# SETUP EVALUATION
# ============================================================================

def setup_evaluation(
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> None:
    """
    Create the initial manual annotation file.

    This function should be run once to create the evaluation set.
    """

    logger.info(
        "Creating evaluation dataset..."
    )

    articles = load_articles()

    representatives = (
        get_representative_articles(
            articles
        )
    )

    sample = create_evaluation_sample(
        representatives,
        sample_size,
    )

    create_labeling_file(
        sample
    )

    logger.info("")
    logger.info(
        "========================================================"
    )

    logger.info(
        "MANUAL ANNOTATION REQUIRED"
    )

    logger.info(
        "========================================================"
    )

    logger.info(
        "Open:"
    )

    logger.info(
        "%s",
        SAMPLE_FILE,
    )

    logger.info("")
    logger.info(
        "Fill the 'gold_category' column with the "
        "correct category."
    )

    logger.info("")
    logger.info(
        "Valid categories:"
    )

    for category in CATEGORIES:

        logger.info(
            "  - %s",
            category,
        )

    logger.info("")
    logger.info(
        "After completing the labels, run:"
    )

    logger.info(
        "python -m src.evaluation.metrics --evaluate"
    )


# ============================================================================
# RUN EVALUATION
# ============================================================================

def run_evaluation() -> None:
    """Run the complete metric calculation."""

    rows = load_gold_labels()

    results = calculate_metrics(
        rows
    )

    save_results(
        results
    )

    save_confusion_matrix(
        results
    )

    print_results(
        results
    )


# ============================================================================
# COMMAND LINE
# ============================================================================

if __name__ == "__main__":

    import sys

    if "--evaluate" in sys.argv:

        run_evaluation()

    else:

        setup_evaluation()