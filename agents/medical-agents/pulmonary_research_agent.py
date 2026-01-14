#!/usr/bin/env python3
"""
Pulmonary Research Agent

Uses Couchbase Agent Catalog for:
- Tool retrieval and management
- Prompt loading from pulmonary_research_agent.yaml
- Agent Tracer for monitoring and observability

"""

import sys
from pathlib import Path
import agentc
import agentc_langchain.chat
import dotenv
from langchain_openai.chat_models import ChatOpenAI

sys.path.insert(0, str(Path(__file__).parent))
dotenv.load_dotenv()

# Initialize catalog once at module level
_catalog = None
_tools_cache = {}


def _get_catalog() -> agentc.Catalog:
    """Get or create the catalog instance"""
    global _catalog
    if _catalog is None:
        _catalog = agentc.Catalog()
    return _catalog


def _get_tool(tool_name: str):
    """Retrieve a tool from the catalog (with caching)"""
    if tool_name not in _tools_cache:
        catalog = _get_catalog()
        tool_obj = catalog.find("tool", name=tool_name)
        # Store the tool object, not just func
        _tools_cache[tool_name] = tool_obj
    return _tools_cache[tool_name].func


def run_pulmonary_research(patient_id: str, question: str, enable_tracing: bool = True) -> dict:
    """
    Run pulmonary research for a patient's condition using Agent Catalog

    Args:
        patient_id: The patient's ID
        question: The doctor's clinical question
        enable_tracing: Whether to enable Agent Tracer (default: True)

    Returns:
        Dictionary with patient_id, condition, question, papers, and answer
    """
    catalog = _get_catalog()

    # Create root span for tracing
    if enable_tracing:
        root_span = catalog.Span(name="pulmonary_research_agent")
        research_span = root_span.new(name=f"patient_{patient_id}_pulmonary_research")
    else:
        root_span = None
        research_span = None

    try:
        # Log workflow start
        if research_span:
            research_span.log(
                agentc.span.SystemContent(
                    value=f"Starting pulmonary research for patient {patient_id}"
                )
            )

        print(f" Starting pulmonary research for patient {patient_id}...")

        from medical_tools import find_patient_by_id, paper_search

        print("   Step 1/4: Getting patient condition...")
        if research_span:
            step_span = research_span.new(name="get_patient_condition")
            # Log tool call with proper content type
            tool_call_id = f"call_find_patient_{patient_id}"
            step_span.log(
                agentc.span.ToolCallContent(
                    tool_name="find_patient_by_id",
                    tool_args={"patient_id": patient_id},
                    tool_call_id=tool_call_id,
                )
            )

        patient = find_patient_by_id(patient_id)

        if not patient:
            error_msg = f"Patient {patient_id} not found"
            if research_span:
                research_span.log(agentc.span.SystemContent(value=f"Error: {error_msg}"))
            return {"error": error_msg}

        condition = patient.get("medical_conditions", "")
        if isinstance(condition, list):
            condition = ", ".join(condition)

        print(f"      Patient: {patient.get('patient_name')}")
        print(f"      Condition: {condition}")

        if research_span:
            # Log tool result with proper content type
            step_span.log(
                agentc.span.ToolResultContent(
                    tool_result={
                        "patient_name": patient.get("patient_name"),
                        "condition": condition,
                    },
                    tool_call_id=tool_call_id,
                )
            )
            step_span.log(
                agentc.span.KeyValueContent(
                    key="patient_condition", value=f"{patient.get('patient_name')} - {condition}"
                )
            )

        print("  Step 2/4: Searching for relevant research papers...")

        search_query = f"{condition}. {question}"
        print(f"     Query: {search_query[:80]}...")

        if research_span:
            search_span = research_span.new(name="vector_search_papers")
            # Log tool call with proper content type
            tool_call_id_search = f"call_paper_search_{patient_id}"
            search_span.log(
                agentc.span.ToolCallContent(
                    tool_name="paper_search",
                    tool_args={"query": search_query, "patient_id": patient_id, "top_k": 3},
                    tool_call_id=tool_call_id_search,
                )
            )

        papers = paper_search(query=search_query, patient_id=patient_id, top_k=3)

        print(f"     Found {len(papers)} relevant papers")

        if research_span:
            search_span.log(
                agentc.span.ToolResultContent(
                    tool_result={
                        "papers_found": len(papers),
                        "paper_titles": [p.get("title", "")[:80] for p in papers],
                    },
                    tool_call_id=tool_call_id_search,
                )
            )
            search_span.log(agentc.span.KeyValueContent(key="papers_found", value=len(papers)))

        print("  Step 3/4: Generating clinical summary...")
        if research_span:
            llm_span = research_span.new(name="generate_summary")

        callbacks = []
        if enable_tracing and llm_span:
            callback = agentc_langchain.chat.Callback(span=llm_span)
            callbacks.append(callback)

        chat_model = ChatOpenAI(model="gpt-4o-mini", temperature=0, callbacks=callbacks)

        context = "\n\n".join(
            [
                f"TITLE: {p.get('title', '')}\n"
                f"CITATION: {p.get('article_citation', '')}\n"
                f"TEXT: {p.get('article_text', '')[:2000]}"
                for p in papers
            ]
        )

        system_prompt = (
            "You are a clinical research assistant. Answer the doctor's question using ONLY the provided paper text. "
            "Be concise and practical. Write exactly three paragraphs."
        )
        user_prompt = (
            f"Patient condition: {condition}\n"
            f"Doctor question: {question}\n\n"
            f"Research papers:\n{context}\n\n"
            f"Provide a concise answer in exactly 3 paragraphs:"
        )

        response = chat_model.invoke([("system", system_prompt), ("user", user_prompt)]).content

        print(f"     Generated clinical summary ({len(response)} chars)")

        if research_span:
            llm_span.log(agentc.span.KeyValueContent(key="summary_length", value=len(response)))

        result = {
            "patient_id": patient_id,
            "patient_name": patient.get("patient_name"),
            "condition": condition,
            "question": question,
            "papers": [
                {
                    "title": p.get("title", ""),
                    "author": p.get("author", ""),
                    "article_citation": p.get("article_citation", ""),
                    "pmc_link": p.get("pmc_link", ""),
                }
                for p in papers
            ],
            "answer": response,
        }

        if research_span:
            research_span.log(
                agentc.span.KeyValueContent(
                    key="research_complete",
                    value=f"{len(papers)} papers, {len(response)} char summary",
                )
            )

        print("  Research complete!")
        return result

    except Exception as e:
        error_msg = f"Error during research: {str(e)}"
        print(f"  {error_msg}")

        if research_span:
            research_span.log(agentc.span.SystemContent(value=f"Error: {error_msg}"))

        return {"error": error_msg}


def main():
    """Test the catalog-integrated research agent"""
    print("=" * 70)
    print("Pulmonary Research Agent - Catalog Integrated Version")
    print("=" * 70)
    print()

    patient_id = "1"
    question = "What are evidence-based treatment options for this patient's condition?"

    print(f"Patient ID: {patient_id}")
    print(f"Question: {question}")
    print()
    print("=" * 70)
    print()

    result = run_pulmonary_research(patient_id, question, enable_tracing=True)

    if "error" in result:
        print(f"\n✗ Error: {result['error']}")
        return

    print("\n" + "=" * 70)
    print("RESEARCH RESULTS")
    print("=" * 70)

    print(f"\n Patient: {result.get('patient_name')} (ID: {result.get('patient_id')})")
    print(f" Condition: {result.get('condition')}")
    print(f" Question: {result.get('question')}")

    print(f"\n Found {len(result.get('papers', []))} Relevant Papers:")
    print("-" * 70)
    for i, paper in enumerate(result.get("papers", []), 1):
        print(f"\n{i}. {paper.get('title')}")
        if paper.get("author"):
            print(f"   Author(s): {paper['author']}")
        if paper.get("article_citation"):
            print(f"   Citation: {paper['article_citation']}")
        if paper.get("pmc_link"):
            print(f"   Link: {paper['pmc_link']}")

    print("\n Clinical Summary:")
    print("-" * 70)
    answer = result.get("answer", "")
    paragraphs = answer.split("\n\n")
    for paragraph in paragraphs:
        if paragraph.strip():
            print(f"\n{paragraph.strip()}")

    print("\n" + "=" * 70)
    print(" Research Complete with Tracing!")
    print("=" * 70)


def run_medical_research(patient_id: str, question: str, enable_tracing: bool = True) -> dict:
    return run_pulmonary_research(patient_id, question, enable_tracing=enable_tracing)


if __name__ == "__main__":
    main()
