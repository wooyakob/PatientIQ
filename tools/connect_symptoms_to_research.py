"""
Tool to connect wearable symptoms/patterns to relevant medical research.

Uses Couchbase vector search to find research papers related to observed
wearable data patterns and patient symptoms. Leverages NVIDIA embeddings
for semantic similarity matching.
"""

import agentc
import couchbase.options
from _shared import cluster, get_nvidia_embedding
from typing import Optional


@agentc.catalog.tool
def connect_symptoms_to_research(
    symptoms_description: str, patient_condition: Optional[str] = None, top_k: int = 3
) -> list[dict]:
    """
    Find relevant research papers based on wearable symptoms and patterns.

    Uses semantic vector search to connect observed symptoms from wearable data
    (e.g., "low oxygen saturation with elevated heart rate") to relevant
    medical research papers. Provides evidence-based context for clinical decisions.

    Args:
        symptoms_description: Description of symptoms/patterns observed in wearable data
                            (e.g., "persistent low O2 saturation below 92% with increased heart rate")
        patient_condition: Patient's medical condition for more relevant results
        top_k: Number of research papers to return (default: 3, max: 10)

    Returns:
        List of relevant research papers, each containing:
        - title: Paper title
        - author: Author names
        - article_text: Relevant excerpts from the paper
        - article_citation: Citation information
        - pmc_link: PubMed Central link
        - relevance_score: How well it matches the symptoms (0-1)
        - key_findings: Extracted key points relevant to the symptoms

    Example:
        >>> connect_symptoms_to_research(
        ...     "low oxygen saturation trending below 92% for multiple days",
        ...     patient_condition="Asthma",
        ...     top_k=3
        ... )
        [
            {
                "title": "Oxygen Saturation Monitoring in Asthma Exacerbations",
                "author": "Smith J, et al.",
                "article_text": "Prolonged hypoxemia (SpO2 <92%) indicates...",
                "article_citation": "J Respir Med 2024;45:123-145",
                "pmc_link": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC...",
                "relevance_score": 0.89,
                "key_findings": [
                    "SpO2 <92% for >3 days requires intervention",
                    "Increased respiratory therapy may be needed"
                ]
            },
            ...
        ]
    """
    if not cluster:
        return [{"error": "Database connection not available"}]

    if not symptoms_description or not symptoms_description.strip():
        return [{"error": "Symptoms description is required"}]

    try:
        # Enhance query with patient condition for better results
        enhanced_query = symptoms_description
        if patient_condition:
            enhanced_query = f"{patient_condition} {symptoms_description}"

        # Generate embedding using NVIDIA model
        try:
            query_vector = get_nvidia_embedding(enhanced_query)
        except Exception as e:
            return [
                {
                    "error": f"Failed to generate embedding: {str(e)}",
                    "message": "Check EMBEDDING_MODEL_ENDPOINT and EMBEDDING_MODEL_TOKEN environment variables",
                }
            ]

        # Perform vector search against research papers
        # Using the hyperscale vector index on vectorized articles
        search_query = """
        SELECT 
            p.title,
            p.author,
            p.article_text,
            p.article_citation,
            p.pmc_link,
            SEARCH_SCORE() AS relevance_score
        FROM `Research`.Pubmed.Pulmonary p
        WHERE SEARCH(p, {{
            "query": {{
                "match_none": {{}}
            }},
            "knn": [{{
                "field": "article_vectorized",
                "vector": $query_vector,
                "k": $top_k
            }}]
        }})
        ORDER BY relevance_score DESC
        LIMIT $top_k
        """

        result = cluster.query(
            search_query,
            couchbase.options.QueryOptions(
                named_parameters={"query_vector": query_vector, "top_k": min(top_k, 10)}
            ),
        )

        rows = list(result.rows())

        if not rows:
            # Fallback to text search if vector search returns nothing
            fallback_query = """
            SELECT p.title, p.author, p.article_text, p.article_citation, p.pmc_link
            FROM `Research`.Pubmed.Pulmonary p
            WHERE LOWER(p.article_text) LIKE '%' || $symptom || '%'
            OR LOWER(p.title) LIKE '%' || $symptom || '%'
            LIMIT $top_k
            """

            # Extract key terms for fallback search
            key_terms = symptoms_description.lower().split()
            search_term = key_terms[0] if key_terms else "hypoxemia"

            result = cluster.query(
                fallback_query,
                couchbase.options.QueryOptions(
                    named_parameters={"symptom": search_term, "top_k": min(top_k, 10)}
                ),
            )

            rows = list(result.rows())

            # Add default relevance score for fallback
            for row in rows:
                row["relevance_score"] = 0.5

        if not rows:
            return [
                {
                    "message": f"No research papers found matching: {symptoms_description}",
                    "suggestion": "Try describing symptoms differently or check if research database is populated",
                }
            ]

        # Process and enrich results
        papers = []
        for row in rows:
            article_text = row.get("article_text", "")

            # Extract key findings (first few sentences that seem relevant)
            key_findings = _extract_key_findings(article_text, symptoms_description)

            papers.append(
                {
                    "title": row.get("title", "Untitled"),
                    "author": row.get("author", "Unknown"),
                    "article_text": article_text[:500] + "..."
                    if len(article_text) > 500
                    else article_text,
                    "full_article_text": article_text,  # Full text for agent processing
                    "article_citation": row.get("article_citation", "Citation not available"),
                    "pmc_link": row.get("pmc_link", ""),
                    "relevance_score": round(row.get("relevance_score", 0), 3),
                    "key_findings": key_findings,
                    "matched_condition": patient_condition if patient_condition else "General",
                }
            )

        return papers

    except Exception as e:
        return [
            {
                "error": f"Failed to search research papers: {str(e)}",
                "symptoms_description": symptoms_description,
                "patient_condition": patient_condition,
            }
        ]


def _extract_key_findings(article_text: str, symptoms: str) -> list[str]:
    """
    Extract key findings from article text relevant to symptoms.

    Simple extraction based on sentence proximity to symptom keywords.
    In production, this could use NLP/LLM for better extraction.
    """
    if not article_text:
        return []

    # Split into sentences
    sentences = article_text.replace("\n", " ").split(". ")

    # Find sentences containing symptom-related keywords
    symptom_keywords = symptoms.lower().split()
    relevant_sentences = []

    for sentence in sentences:
        sentence_lower = sentence.lower()
        # Check if sentence contains any symptom keywords
        if any(keyword in sentence_lower for keyword in symptom_keywords):
            # Clean and add sentence
            clean_sentence = sentence.strip()
            if len(clean_sentence) > 20 and len(clean_sentence) < 300:
                relevant_sentences.append(clean_sentence)
                if len(relevant_sentences) >= 3:
                    break

    # If no matches, return first few sentences as key findings
    if not relevant_sentences and sentences:
        relevant_sentences = [s.strip() for s in sentences[:2] if len(s.strip()) > 20]

    return relevant_sentences[:3]  # Max 3 key findings
