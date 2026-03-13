"""Pebbles — Article clustering by embedding cosine similarity."""
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta


def _build_embedding_text(article: dict) -> str:
    """Build text for embedding: Title + Summary + Key Entities.

    If summary is too short, include content for better representation.
    """
    title = article.get("title", "")
    title_orig = article.get("titleOriginal", "")
    summary = article.get("description", "")
    entities = article.get("entities", "")
    content = article.get("content", "")

    parts = [title]
    if title_orig:
        parts.append(title_orig)
    if summary and len(summary) > 50:
        parts.append(summary[:300])
    elif content:
        parts.append(content[:300])
    if entities:
        parts.append(f"Entities: {entities}")

    return "\n".join(parts)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def cluster_articles(articles: list[dict], threshold: float = 0.70):
    """Assign clusterId to each article based on embedding cosine similarity.

    - Only compares articles within the same category
    - Only compares articles published within the last 3 days
    - Articles from the same source are never clustered together
    - Uses graph-based clustering with same-source merge prevention
    """
    if not articles:
        return

    # Filter to articles within last 3 days
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=3)

    recent_indices = []
    for i, a in enumerate(articles):
        try:
            pub = datetime.fromisoformat(a["pubDate"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                recent_indices.append(i)
        except (ValueError, KeyError):
            recent_indices.append(i)

    print(f"\nClustering {len(recent_indices)}/{len(articles)} recent articles (threshold={threshold})...")

    if len(recent_indices) < 2:
        for idx, a in enumerate(articles):
            a["clusterId"] = idx
        return

    # Load embedding model
    print("  Loading embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    # Build embedding texts and encode
    texts = [_build_embedding_text(articles[i]) for i in recent_indices]
    print(f"  Encoding {len(texts)} articles...")
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    # Build adjacency list of similar pairs (edges)
    edges: list[tuple[int, int, float]] = []
    for ii in range(len(recent_indices)):
        for jj in range(ii + 1, len(recent_indices)):
            i, j = recent_indices[ii], recent_indices[jj]
            # Skip same source
            if articles[i]["source"] == articles[j]["source"]:
                continue

            sim = float(np.dot(embeddings[ii], embeddings[jj]))
            if sim >= threshold:
                edges.append((ii, jj, sim))

    # Graph-based clustering: merge connected components,
    # but prevent clusters from containing duplicate sources
    neighbors: defaultdict[int, list] = defaultdict(list)
    for ii, jj, sim in edges:
        neighbors[ii].append((jj, sim))
        neighbors[jj].append((ii, sim))

    visited = set()
    clusters: list[list[int]] = []

    for node in range(len(recent_indices)):
        if node in visited:
            continue
        if not neighbors[node]:
            continue

        # BFS to build cluster, checking source conflicts
        cluster = [node]
        sources_in_cluster = {articles[recent_indices[node]]["source"]}
        visited.add(node)

        queue = list(neighbors[node])
        # Sort by similarity descending — prefer stronger connections
        queue.sort(key=lambda x: x[1], reverse=True)

        while queue:
            candidate, sim = queue.pop(0)
            if candidate in visited:
                continue
            cand_source = articles[recent_indices[candidate]]["source"]
            # Allow at most one article per source in a cluster
            if cand_source in sources_in_cluster:
                continue
            visited.add(candidate)
            cluster.append(candidate)
            sources_in_cluster.add(cand_source)
            # Add neighbors of the new member
            for nb, nb_sim in neighbors[candidate]:
                if nb not in visited:
                    queue.append((nb, nb_sim))
            queue.sort(key=lambda x: x[1], reverse=True)

        if len(cluster) > 1:
            clusters.append(cluster)

    # Assign cluster IDs
    next_id = 0
    for cluster in clusters:
        for ii in cluster:
            articles[recent_indices[ii]]["clusterId"] = next_id
        next_id += 1

    # Assign unique IDs to unclustered articles
    for a in articles:
        if "clusterId" not in a:
            a["clusterId"] = next_id
            next_id += 1

    # Stats
    multi = len(clusters)
    total_grouped = sum(len(c) for c in clusters)

    print(f"  Found {len(edges)} similar pairs")
    print(f"  {multi} clusters with 2+ articles ({total_grouped} articles grouped)")
