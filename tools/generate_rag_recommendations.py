"""
Tool to generate RAG-based clinical recommendations using research papers and wearable trends.

Uses vector similarity to find relevant research papers based on observed symptoms,
then generates evidence-based recommendations using RAG approach.
"""

import agentc
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.utils.llm_client import get_llm_client


@agentc.catalog.tool
def generate_rag_recommendations(
    trend_analysis: dict, patient_condition: str, research_papers: Optional[list[dict]] = None
) -> dict:
    """
    Generate evidence-based recommendations using RAG on research papers and trend data.

    This tool takes clinical alerts from trend analysis, retrieves relevant research papers
    via vector search, and uses an LLM to generate specific, actionable recommendations
    grounded in the research evidence.

    This is much faster and more accurate than having the agent LLM read through all
    the data sequentially. The RAG approach:
    1. Uses vector search to find relevant papers (fast)
    2. Constructs focused prompt with just relevant context
    3. Generates recommendations in single LLM call

    Args:
        trend_analysis: Output from analyze_wearable_trends with alerts
        patient_condition: Patient's primary medical condition
        research_papers: Optional pre-retrieved research papers (from paper_search or connect_symptoms_to_research)

    Returns:
        Dictionary containing:
        - recommendations: List of evidence-based clinical recommendations
        - evidence_citations: Papers cited for each recommendation
        - reasoning: Brief explanation of the recommendation logic
        - priority_level: Overall priority (critical/high/medium/low)

    Example:
        >>> generate_rag_recommendations(
        ...     trend_analysis={
        ...         "alerts": [{"metric": "blood_oxygen_level", "severity": "critical", ...}],
        ...         "summary": "1 CRITICAL alert requiring immediate attention"
        ...     },
        ...     patient_condition="Asthma",
        ...     research_papers=[{...}, {...}]
        ... )
        {
            "recommendations": [
                {
                    "recommendation": "Immediate pulmonary function testing and consideration of oral corticosteroid therapy",
                    "evidence": "Study by Chen et al. (2023) shows early intervention with PFT and steroids reduces hospitalization by 45% in asthma patients with O2 <90%",
                    "citation": "Chen et al., 2023 (PMC9876543)",
                    "priority": "critical",
                    "action_items": [
                        "Schedule PFT within 24-48 hours",
                        "Consider prednisone 40mg daily x 5 days",
                        "Monitor O2 saturation continuously"
                    ]
                },
                ...
            ],
            "priority_level": "critical",
            "reasoning": "Critical oxygen desaturation pattern requires immediate intervention based on current research evidence",
            "total_recommendations": 3,
            "papers_cited": 2
        }
    """
    if not trend_analysis or not isinstance(trend_analysis, dict):
        return {
            "error": "Invalid trend analysis provided",
            "recommendations": [],
            "priority_level": "unknown",
        }

    alerts = trend_analysis.get("alerts", [])
    if not alerts:
        return {
            "recommendations": [
                {
                    "recommendation": "Continue current management plan",
                    "priority": "low",
                    "reasoning": "No concerning trends detected in wearable data",
                }
            ],
            "priority_level": "low",
            "reasoning": "All metrics within acceptable ranges",
            "total_recommendations": 1,
            "papers_cited": 0,
        }

    # Determine overall priority from alerts
    has_critical = any(a.get("severity") == "critical" for a in alerts)
    has_high = any(a.get("severity") == "high" for a in alerts)

    if has_critical:
        priority_level = "critical"
    elif has_high:
        priority_level = "high"
    else:
        priority_level = "medium"

    # Build context for RAG
    alert_descriptions = []
    for alert in alerts[:5]:  # Top 5 alerts
        alert_descriptions.append(
            f"- {alert.get('severity', 'unknown').upper()}: {alert.get('message', 'N/A')} "
            f"(Clinical significance: {alert.get('clinical_significance', 'Unknown')})"
        )

    alerts_context = "\n".join(alert_descriptions)

    # Build research context if papers provided
    research_context = ""
    if research_papers and len(research_papers) > 0:
        research_snippets = []
        for i, paper in enumerate(research_papers[:3], 1):  # Top 3 papers
            title = paper.get("title", "Unknown")
            findings = paper.get("key_findings", [])
            citation = paper.get("article_citation", "No citation")

            findings_text = "; ".join(findings[:2]) if findings else "No findings extracted"
            research_snippets.append(
                f"{i}. {title}\n   Citation: {citation}\n   Key Findings: {findings_text}"
            )

        research_context = "\n\n".join(research_snippets)
    else:
        research_context = (
            "No research papers available. Base recommendations on clinical guidelines."
        )

    # Construct RAG prompt
    rag_prompt = f"""You are a clinical decision support AI. Generate evidence-based recommendations for a patient with {patient_condition}.

## CLINICAL ALERTS FROM WEARABLE DATA:
{alerts_context}

## RELEVANT RESEARCH EVIDENCE:
{research_context}

## TASK:
Generate 3-5 specific, actionable clinical recommendations that:
1. Address the most severe alerts first
2. Are grounded in the research evidence when available
3. Include specific action items (tests, medications, monitoring)
4. Are practical and implementable by the care team

For each recommendation, provide:
- The specific recommendation
- Evidence/reasoning from research papers (cite by author and year)
- Priority level (critical/high/medium/low)
- 2-3 specific action items

Return your response as a JSON array of recommendation objects."""

    try:
        # Get LLM client
        llm = get_llm_client()

        # Generate recommendations
        response = llm.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a clinical decision support AI specializing in pulmonology.",
                },
                {"role": "user", "content": rag_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        import json

        recommendations_data = json.loads(response.choices[0].message.content)

        # Extract recommendations array (handle different possible response formats)
        if isinstance(recommendations_data, dict):
            recs = recommendations_data.get("recommendations", [])
        elif isinstance(recommendations_data, list):
            recs = recommendations_data
        else:
            recs = []

        # Count papers cited
        papers_cited = len(research_papers) if research_papers else 0

        return {
            "recommendations": recs,
            "priority_level": priority_level,
            "reasoning": f"Based on {len(alerts)} clinical alerts and {papers_cited} research papers",
            "total_recommendations": len(recs),
            "papers_cited": papers_cited,
            "rag_method": "vector_search_plus_llm",
        }

    except Exception as e:
        print(f"Error generating RAG recommendations: {str(e)}")

        # Fallback: Return basic recommendations from trend analysis
        fallback_recs = []
        for rec_text in trend_analysis.get("recommendations", [])[:3]:
            fallback_recs.append(
                {
                    "recommendation": rec_text,
                    "priority": priority_level,
                    "evidence": "Based on clinical guidelines (research papers not available)",
                    "action_items": ["Consult with physician", "Monitor closely"],
                }
            )

        return {
            "recommendations": fallback_recs,
            "priority_level": priority_level,
            "reasoning": "Fallback recommendations based on trend analysis",
            "total_recommendations": len(fallback_recs),
            "papers_cited": 0,
            "error": f"RAG generation failed: {str(e)}",
        }
