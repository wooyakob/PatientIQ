"""
Healthcare Research Agent using vector search with Couchbase AI Services.
Implements semantic search over medical research using embeddings.
"""

import os
import json
import re
from datetime import datetime, timezone
import agentc
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from tools.research_tools import fetch_research_articles
from tools.doctor_notes_tools import search_doctor_notes

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def get_llm(model: str = "gpt-4", temperature: float = 0.7):
    """Get OpenAI LLM instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)


class HealthcareAgentOrchestrator:
    """
    Orchestrator for healthcare AI agents.

    Two specialized agents:
    1. Medical Researcher Agent - Uses vector search on Research.Pubmed.Pulmonary
    2. Doctor Notes Buddy Agent - Uses vector search on Scripps.Notes.Doctor

    Both use Couchbase AI Services embedding model (2048 dimensions) for semantic search.
    """

    def __init__(self):
        """Initialize the orchestrator with catalog connection"""
        try:
            self.catalog = agentc.Catalog()
            print("Connected to agent catalog")
            print("  - Loaded: Medical Researcher Agent (vector search)")
            print("  - Loaded: Doctor Notes Buddy Agent (vector search)")
        except Exception as e:
            print(f"Warning: Could not connect to agent catalog: {e}")
            print("Will operate without catalog features")
            self.catalog = None

        self.llm = get_llm()


    def _extract_article_summary(self, article_text: str, max_length: int = 800) -> str:
        """Extract a meaningful portion from the article for summarization"""
        article_text = article_text.replace("\r", "\n")
        article_text = re.sub(r"https?://\S+", "", article_text)
        article_text = re.sub(r"\s+http\S+", "", article_text)
        article_text = re.sub(r"[ \t]{2,}", " ", article_text)
        article_text = re.sub(r"\n{3,}", "\n\n", article_text)

        # Try to find abstract or introduction
        if "Abstract" in article_text or "ABSTRACT" in article_text:
            start = max(article_text.find("Abstract"), article_text.find("ABSTRACT"))
            tail = article_text[start:]
            tail_lines = []
            for line in tail.split("\n"):
                stripped_line = line.strip()
                if not stripped_line:
                    tail_lines.append("")
                    continue
                if "orcid.org" in stripped_line.lower():
                    continue
                if stripped_line.lower().startswith("===="):
                    continue
                tail_lines.append(stripped_line)
            cleaned = "\n".join(tail_lines)
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
            return cleaned[:max_length]

        # Otherwise take first substantial paragraphs
        paragraphs = [p.strip() for p in article_text.split("\n\n") if len(p.strip()) > 100]
        if paragraphs:
            return paragraphs[0][:max_length]

        return article_text[:max_length]

    def _normalize_summary_text(self, text: str) -> str:
        normalized = text.replace("\r", "\n").strip()
        normalized = re.sub(r"\n{2,}", "\n\n", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        return normalized

    def _looks_like_raw_article(self, text: str) -> bool:
        t = text.lower()
        if "====" in t or "http://" in t or "https://" in t:
            return True
        if text.count("\n") > 4:
            return True
        if len(text) > 900:
            return True
        if t.startswith("pmid") or t.startswith("article"):
            return True
        return False

    def _parse_json_object(self, content: str) -> dict | None:
        try:
            return json.loads(content)
        except Exception:
            pass

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _count_sentences(self, text: str) -> int:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
        return len(parts)

    def _generate_clean_summaries_from_articles(
        self,
        *,
        patient_name: str,
        patient_age: str | int,
        condition: str,
        article_contents: list[str],
    ) -> tuple[str, list[str]]:
        system_prompt = (
            "You are a clinical medical research summarization assistant for physicians. "
            "You must produce concise, high-signal summaries."
        )

        context = "\n\n".join(article_contents[:3])

        user_prompt = (
            "Create a clean medical research summary for this patient.\n\n"
            f"Patient: {patient_name} ({patient_age})\n"
            f"Condition: {condition}\n\n"
            "Source excerpts (may contain metadata/noise):\n"
            f"{context}\n\n"
            "Return STRICT JSON ONLY with this exact schema:\n"
            "{\n"
            '  "research_topic": string,\n'
            '  "summaries": [string, string, string]\n'
            "}\n\n"
            "Rules:\n"
            "- Each summary must be 2–3 sentences.\n"
            "- Do not number the summaries (no '1.', '2.', '3.').\n"
            "- No URLs, no author lists, no journal front matter, no section headers like '==== Front'.\n"
            "- Do not invent trial names, statistics, or claims that are not supported by the excerpts.\n"
            "- Use physician-appropriate clinical language.\n"
            "- Make sure all 3 summaries are relevant to the condition provided."
        )

        last_topic = f"{condition} Treatment Advances"
        last_summaries: list[str] = []
        for attempt in range(2):
            attempt_prompt = user_prompt
            if attempt == 1:
                attempt_prompt = (
                    user_prompt
                    + "\n\nYour previous output did not fully comply. Rewrite STRICT JSON so that each summary is exactly 2–3 sentences and tightly specific to the condition (no speculative cross-cancer applicability)."
                )

            response = self.llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=attempt_prompt)]
            )
            data = self._parse_json_object(str(response.content).strip()) or {}

            topic = str(data.get("research_topic") or f"{condition} Treatment Advances").strip()
            summaries_raw = data.get("summaries") if isinstance(data.get("summaries"), list) else []

            summaries: list[str] = []
            for s in summaries_raw:
                if not isinstance(s, str):
                    continue
                normalized = self._normalize_summary_text(s)
                normalized = normalized.replace("\n", " ").strip()
                normalized = re.sub(r"^\s*\d+[\.)\-:]\s*", "", normalized)
                normalized = re.sub(r"\s{2,}", " ", normalized)
                if normalized:
                    summaries.append(normalized)

            summaries = summaries[:3]
            last_topic = topic
            last_summaries = summaries

            if len(summaries) == 3 and all(2 <= self._count_sentences(s) <= 3 for s in summaries):
                return topic, summaries

        summaries = last_summaries[:3]
        while len(summaries) < 3:
            summaries.append(
                f"Recent clinical research in {condition} continues to refine treatment selection and improve outcomes; consider individualizing therapy based on tumor biology and patient comorbidities."
            )

        return last_topic, summaries

    async def run_research_summarizer(self, patient_id: str, patient_data: dict) -> dict:
        """
        Run the Medical Researcher Agent.

        Agent Prompt: medical_researcher_agent.yaml
        Tool: fetch_research_articles (vector search)

        This agent:
        1. Uses vector search (2048-dim embeddings) to find relevant research
        2. Searches Research.Pubmed.Pulmonary using hyperscale index
        3. Analyzes semantically similar research articles
        4. Uses AI to create summaries of real research
        5. Returns patient-specific research insights

        Args:
            patient_id: Patient identifier
            patient_data: Patient information

        Returns:
            Dictionary with research topic and AI-generated summaries from real papers
        """
        try:
            condition = patient_data.get("condition") or patient_data.get("medical_conditions") or "Unknown"
            patient_age = patient_data.get("age", "Unknown")
            patient_name = patient_data.get("name", "Unknown")

            print("   Fetching research excerpts from Couchbase...")
            tool_result = fetch_research_articles(condition=condition, limit=5, max_chars=1600)
            excerpts = tool_result.get("excerpts") if isinstance(tool_result, dict) else None
            excerpts = excerpts if isinstance(excerpts, list) else []

            if not excerpts:
                print(f"   No research excerpts found for {condition}")
                return self._generate_fallback_research(patient_data)

            article_contents = []
            for i, excerpt in enumerate(excerpts[:5]):
                if not isinstance(excerpt, str):
                    continue
                content = self._extract_article_summary(excerpt)
                if content:
                    article_contents.append(f"Article {i + 1}:\n{content}")

            if not article_contents:
                print("   No usable excerpts extracted")
                return self._generate_fallback_research(patient_data)

            print("   Generating AI summaries from Couchbase research excerpts...")
            research_topic, summaries = self._generate_clean_summaries_from_articles(
                patient_name=patient_name,
                patient_age=patient_age,
                condition=condition,
                article_contents=article_contents,
            )

            return {
                "research_topic": research_topic,
                "summaries": summaries,
                "condition": condition,
                "patient_id": patient_id,
                "articles_analyzed": len(article_contents),
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

        except Exception as e:
            print(f"   Error in research summarizer: {e}")
            import traceback

            traceback.print_exc()
            return self._generate_fallback_research(patient_data)

    def _generate_fallback_research(self, patient_data: dict) -> dict:
        """Generate generic research when PubMed data unavailable"""
        condition = patient_data.get("condition", "Unknown")
        return {
            "research_topic": f"{condition} Research",
            "summaries": [
                f"Recent clinical studies continue to advance treatment options for {condition}.",
                f"Current research focuses on improving outcomes and quality of life for patients with {condition}.",
                f"Ongoing trials are investigating novel therapeutic approaches for {condition} management.",
            ],
            "condition": condition,
            "patient_id": patient_data.get("id", ""),
            "articles_analyzed": 0,
        }

    async def answer_doctor_notes_query(self, query: str, patient_id: str = None) -> dict:
        """
        Run the Doctor Notes Buddy Agent.

        Agent Prompt: doctor_notes_buddy_agent.yaml
        Tool: search_doctor_notes (vector search)

        This agent:
        1. Uses vector search (2048-dim embeddings) to find relevant doctor notes
        2. Searches Scripps.Notes.Doctor using hyperscale index
        3. Finds semantically similar notes even with different terminology
        4. Passes the notes to LLM for answering the question
        5. Returns a natural language answer with supporting notes

        Args:
            query: Doctor's question (e.g., "How is the patient responding to treatment?")
            patient_id: Optional patient ID to filter notes

        Returns:
            Dictionary with answer and supporting notes
        """
        try:
            print(f"   Searching doctor notes for: {query}")

            # Search doctor notes using vector search
            search_result = search_doctor_notes(
                query=query,
                patient_id=patient_id,
                limit=5,
                max_chars=1500,
            )

            if not search_result.get("found"):
                return {
                    "query": query,
                    "answer": "No relevant doctor notes found to answer this question.",
                    "supporting_notes": [],
                    "patient_id": patient_id,
                }

            notes = search_result.get("notes", [])

            # Format notes for LLM context
            notes_context = "\n\n".join([
                f"Note {idx + 1} (Date: {note.get('visit_date', 'Unknown')}, Patient: {note.get('patient_id', 'Unknown')}):\n{note.get('visit_notes', '')}"
                for idx, note in enumerate(notes)
            ])

            # Build prompt for LLM
            system_prompt = (
                "You are a clinical assistant helping doctors review and understand patient notes. "
                "Answer questions based on the provided doctor notes. "
                "Be concise, factual, and cite which note(s) support your answer."
            )

            user_prompt = (
                f"Question: {query}\n\n"
                "Relevant Doctor Notes:\n"
                f"{notes_context}\n\n"
                "Please provide a clear, concise answer based on these notes. "
                "Reference specific notes when applicable (e.g., 'Note 1 indicates...')."
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Get answer from LLM
            response = self.llm.invoke(messages)
            answer = response.content

            return {
                "query": query,
                "answer": answer,
                "supporting_notes": notes,
                "notes_count": len(notes),
                "patient_id": patient_id,
                "search_type": "vector_search",
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

        except Exception as e:
            print(f"   Error answering doctor notes query: {e}")
            import traceback
            traceback.print_exc()
            return {
                "query": query,
                "answer": f"Error processing query: {str(e)}",
                "supporting_notes": [],
                "patient_id": patient_id,
            }


# Global orchestrator instance
orchestrator = HealthcareAgentOrchestrator()
