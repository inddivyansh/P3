"""Semantic near-duplicate detection using sentence-transformers."""
"""
D-P1-22 — News Feed to Digest Pipeline

Semantic article deduplication.

Purpose:
    Detect articles that are different URLs/headlines but describe
    the same underlying news story.

Method:
    1. Generate sentence embeddings using MiniLM.
    2. Calculate cosine similarity between articles.
    3. Group highly similar articles into story clusters.
    4. Select one representative article from each cluster.

The original articles are retained. Each article receives:
    - story_cluster_id
    - is_cluster_representative

This allows the digest to use one representative story while
retaining all source coverage for auditing.
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cleaned_articles.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "deduplicated_articles.json"
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "all-MiniLM-L6-v2"

# Articles above this similarity are considered potential duplicates.
SIMILARITY_THRESHOLD = 0.82


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load articles
# ---------------------------------------------------------------------------

def load_articles(
    input_path: Path = INPUT_FILE,
) -> list[dict[str, Any]]:
    """Load cleaned articles."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run cleaner.py first."
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

    if not isinstance(articles, list):
        raise ValueError(
            "Invalid cleaned_articles.json format."
        )

    logger.info(
        "Loaded %d article(s)",
        len(articles),
    )

    return articles


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def load_embedding_model() -> SentenceTransformer:
    """
    Load the local MiniLM sentence-embedding model.

    The first execution downloads the model.
    Subsequent executions use the local cache.
    """

    logger.info(
        "Loading embedding model: %s",
        MODEL_NAME,
    )

    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"

    logger.info("Using device: %s", device)

    model = SentenceTransformer(
        MODEL_NAME,
        device=device,
    )

    logger.info(
        "Embedding model loaded."
    )

    return model


def create_embeddings(
    articles: list[dict[str, Any]],
    model: SentenceTransformer,
) -> np.ndarray:
    """
    Generate an embedding for each article.

    We use classifier_text because it contains both:
        - headline
        - article body
    """

    texts = [
        article.get(
            "classifier_text",
            article.get("article_text", ""),
        )
        for article in articles
    ]

    logger.info(
        "Generating embeddings for %d article(s)...",
        len(texts),
    )

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    logger.info(
        "Embedding generation complete."
    )

    return np.asarray(embeddings)


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def create_story_clusters(
    articles: list[dict[str, Any]],
    embeddings: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Group semantically similar articles.

    A simple greedy clustering strategy is used for the prototype.

    Each article is compared against existing cluster representatives.
    If similarity is above the threshold, it joins that cluster.
    Otherwise, a new cluster is created.

    This is intentionally simple for Phase 0.
    """

    if len(articles) == 0:
        return []

    cluster_representatives: list[int] = []

    cluster_ids: list[int] = [
        -1
    ] * len(articles)

    cluster_count = 0

    for index in range(len(articles)):

        # First article always starts the first cluster.
        if not cluster_representatives:

            cluster_representatives.append(index)
            cluster_ids[index] = cluster_count
            cluster_count += 1

            continue

        representative_embeddings = embeddings[
            cluster_representatives
        ]

        current_embedding = embeddings[
            index:index + 1
        ]

        similarities = cosine_similarity(
            current_embedding,
            representative_embeddings,
        )[0]

        best_cluster_position = int(
            np.argmax(similarities)
        )

        best_similarity = float(
            similarities[
                best_cluster_position
            ]
        )

        if best_similarity >= threshold:

            cluster_id = (
                best_cluster_position
            )

            cluster_ids[index] = cluster_id

        else:

            cluster_id = cluster_count

            cluster_ids[index] = cluster_id

            cluster_representatives.append(
                index
            )

            cluster_count += 1

    # Add cluster metadata to each article.
    clustered_articles = []

    for index, article in enumerate(articles):

        processed_article = dict(article)

        cluster_id = cluster_ids[index]

        processed_article[
            "story_cluster_id"
        ] = f"story_{cluster_id + 1:05d}"

        processed_article[
            "is_cluster_representative"
        ] = (
            cluster_representatives[
                cluster_id
            ] == index
        )

        clustered_articles.append(
            processed_article
        )

    logger.info(
        "Created %d story cluster(s) from %d article(s)",
        cluster_count,
        len(articles),
    )

    return clustered_articles


# ---------------------------------------------------------------------------
# Cluster statistics
# ---------------------------------------------------------------------------

def log_cluster_statistics(
    articles: list[dict[str, Any]],
) -> None:
    """Print useful deduplication statistics."""

    cluster_sizes: dict[str, int] = {}

    for article in articles:

        cluster_id = article.get(
            "story_cluster_id"
        )

        cluster_sizes[cluster_id] = (
            cluster_sizes.get(
                cluster_id,
                0,
            )
            + 1
        )

    duplicate_articles = sum(
        size - 1
        for size in cluster_sizes.values()
        if size > 1
    )

    logger.info(
        "Unique stories: %d",
        len(cluster_sizes),
    )

    logger.info(
        "Duplicate/secondary articles: %d",
        duplicate_articles,
    )

    if cluster_sizes:

        largest_cluster = max(
            cluster_sizes.values()
        )

        logger.info(
            "Largest story cluster: %d article(s)",
            largest_cluster,
        )


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_articles(
    articles: list[dict[str, Any]],
    output_path: Path = OUTPUT_FILE,
) -> None:
    """Save deduplicated article metadata."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "article_count": len(articles),
        "articles": articles,
    }

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
        "Saved deduplicated dataset to %s",
        output_path,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_deduplication() -> list[dict[str, Any]]:
    """Run the complete semantic deduplication stage."""

    articles = load_articles()

    if not articles:
        logger.warning(
            "No articles available for deduplication."
        )

        save_articles([])

        return []

    model = load_embedding_model()

    embeddings = create_embeddings(
        articles,
        model,
    )

    clustered_articles = create_story_clusters(
        articles,
        embeddings,
        threshold=SIMILARITY_THRESHOLD,
    )

    log_cluster_statistics(
        clustered_articles
    )

    save_articles(
        clustered_articles
    )

    return clustered_articles


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_deduplication()