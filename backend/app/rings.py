"""Copy rings detection module for Local Echo Scan.

Constructs an undirected graph where students are nodes and flagged pairs
are edges, then identifies connected components of size >= min_ring_size
as groups of students sharing highly similar content.
"""

from __future__ import annotations

import logging
import networkx as nx

from .models import CopyRing, FlaggedPair

logger = logging.getLogger(__name__)

DEFAULT_MIN_RING_SIZE = 3
NEUTRAL_DESCRIPTION = "Group of students with highly similar content"


def find_copy_rings(
    flagged_pairs: list[FlaggedPair],
    min_ring_size: int = DEFAULT_MIN_RING_SIZE,
    explanations_available: bool = False,
) -> list[CopyRing]:
    """Identify clusters/rings of students sharing highly similar content.

    Builds an undirected graph where students are nodes and flagged pairs
    are edges. Connected components with at least min_ring_size students
    are returned as CopyRing objects.

    Args:
        flagged_pairs: Flagged student pairs above similarity threshold.
        min_ring_size: Minimum number of students required to form a ring (default 3).
        explanations_available: Whether LLM explanations are available.
            If True, pairs classified as 'coincidence' are excluded from edges.

    Returns:
        List of CopyRing objects, sorted by size descending, then average score descending.
    """
    if not flagged_pairs:
        return []

    # Filter edges: exclude pairs labeled 'coincidence' if explanations were active
    filtered_pairs: list[FlaggedPair] = []
    for fp in flagged_pairs:
        if explanations_available and (fp.label or "").strip().lower() == "coincidence":
            logger.info(
                "Excluding pair %s - %s from ring graph (labeled as coincidence)",
                fp.student_a,
                fp.student_b,
            )
            continue
        filtered_pairs.append(fp)

    if not filtered_pairs:
        return []

    # Build undirected graph
    graph = nx.Graph()
    for fp in filtered_pairs:
        graph.add_edge(
            fp.student_a,
            fp.student_b,
            score=fp.score,
            pair=fp,
        )

    # Detect connected components
    rings: list[CopyRing] = []
    for component in nx.connected_components(graph):
        if len(component) >= min_ring_size:
            members = sorted(list(component))
            subgraph = graph.subgraph(component)
            
            # Edges inside this component
            edge_scores = [
                d["score"] for _, _, d in subgraph.edges(data=True)
            ]
            pair_count = len(edge_scores)
            avg_score = round(sum(edge_scores) / pair_count, 4) if pair_count > 0 else 0.0

            rings.append(
                CopyRing(
                    members=members,
                    size=len(members),
                    pair_count=pair_count,
                    average_score=avg_score,
                    description=NEUTRAL_DESCRIPTION,
                )
            )

    # Sort rings: largest first, then highest average score
    rings.sort(key=lambda r: (r.size, r.average_score), reverse=True)
    return rings
