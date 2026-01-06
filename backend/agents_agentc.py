"""
Healthcare agents implemented using agentc (agent-catalog) pattern.
These agents use prompts and tools registered in the catalog.
"""

import os
import uuid
import json
import re
from datetime import datetime, timezone
import agentc
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

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
    Orchestrator for healthcare agents using agentc catalog.
    Loads prompts and tools from the catalog and creates agent instances.
    """

    def __init__(self):
        """Initialize the orchestrator with catalog connection"""
        try:
            self.catalog = agentc.Catalog()
            print("Connected to agent catalog")
        except Exception as e:
            print(f"Warning: Could not connect to agent catalog: {e}")
            print("Will operate without catalog features")
            self.catalog = None

        self.llm = get_llm()

    def _get_catalog_tools(self, tool_names: list[str]) -> list:
        """Retrieve tools from the catalog by name"""
        tools = []
        if not self.catalog:
            return tools

        for tool_name in tool_names:
            try:
                tool = self.catalog.find("tool", name=tool_name)
                if tool:
                    tools.append(tool)
            except Exception as e:
                print(f"Warning: Could not load tool '{tool_name}': {e}")

        return tools

    def _format_prompt(self, prompt_content: str, variables: dict) -> str:
        """Format prompt content with variables"""
        try:
            return prompt_content.format(**variables)
        except KeyError as e:
            print(f"Warning: Missing variable in prompt: {e}")
            return prompt_content

    async def run_wearable_monitor(self, patient_id: str, patient_data: dict) -> dict:
        """
        Run the Wearable Data Monitoring Agent.

        Args:
            patient_id: Patient identifier
            patient_data: Patient information including wearable data

        Returns:
            Dictionary with analysis and alerts
        """
        try:
            # Get prompt from catalog
            prompt_record = None
            if self.catalog:
                try:
                    prompt_record = self.catalog.find("prompt", name="wearable_monitor_agent")
                except Exception as e:
                    print(f"Could not load prompt from catalog: {e}")

            # Prepare prompt variables
            wearable_data = patient_data.get("wearable_data", {})
            prompt_vars = {
                "patient_name": patient_data.get("name", "Unknown"),
                "patient_age": patient_data.get("age", "Unknown"),
                "patient_condition": patient_data.get("condition", "Unknown"),
                "heart_rate": wearable_data.get("heart_rate", []),
                "step_count": wearable_data.get("step_count", [])
            }

            # Build prompt
            if prompt_record:
                system_content = prompt_record.get("agent_instructions", "")
                user_content = self._format_prompt(
                    prompt_record.get("content", ""), prompt_vars
                )
            else:
                # Fallback prompt
                system_content = "You are a medical AI assistant analyzing wearable health data."
                user_content = f"""
                Analyze wearable data for patient {prompt_vars['patient_name']}.
                Condition: {prompt_vars['patient_condition']}
                Heart Rate: {prompt_vars['heart_rate']}
                Step Count: {prompt_vars['step_count']}

                Determine if any alerts are needed.
                """

            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_content)
            ]

            # Run LLM
            response = self.llm.invoke(messages)

            # Parse response and generate alerts
            analysis = response.content
            alerts = []

            # Simple alert detection (in production, use structured output)
            if any(keyword in analysis.lower() for keyword in
                   ["alert", "concerning", "critical", "urgent", "elevated"]):

                alert_id = str(uuid.uuid4())
                alert = {
                    "id": alert_id,
                    "patient_id": patient_id,
                    "alert_type": "Wearable Data Alert",
                    "message": analysis[:500],  # Truncate for summary
                    "severity": "medium",
                    "timestamp": "",
                    "metrics": {
                        "heart_rate": wearable_data.get("heart_rate", []),
                        "step_count": wearable_data.get("step_count", [])
                    }
                }
                alerts.append(alert)

            return {
                "analysis": analysis,
                "alerts": alerts,
                "patient_id": patient_id
            }

        except Exception as e:
            print(f"Error in wearable monitor: {e}")
            return {
                "error": str(e),
                "analysis": "",
                "alerts": []
            }

    def _load_pubmed_articles(self):
        """Load PubMedCentral.json articles"""
        import json
        try:
            pubmed_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "PubMedCentral.json"
            )
            with open(pubmed_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            return articles
        except Exception as e:
            print(f"Error loading PubMedCentral.json: {e}")
            return []

    def _find_relevant_articles(self, condition: str, articles: list, max_articles: int = 5) -> list:
        """
        Find articles relevant to patient condition using keyword matching.
        """
        # Define keywords for different conditions
        condition_keywords = {
            "Breast Cancer Stage II": [
                "breast cancer",
                "breast carcinoma",
                "mammary",
                "stage ii",
                "early breast",
                "early-stage",
                "early stage",
                "adjuvant",
                "neoadjuvant",
                "pathologic complete response",
                "pcr",
                "onotype",
                "endocrine therapy",
                "aromatase inhibitor",
                "tamoxifen",
                "radiotherapy",
                "sentinel",
                "her2",
                "trastuzumab",
                "pertuzumab",
                "triple negative",
                "tnbc",
                "brca",
                "ductal",
                "lobular",
                "estrogen receptor",
                "progesterone receptor",
            ],
            "Type 2 Diabetes": ["diabetes", "diabetes mellitus", "glucose", "insulin", "glycemic", "metabolic", "hyperglycemia"],
            "Anxiety Disorder": ["anxiety", "anxious", "panic", "mental health", "psychiatric", "stress", "depression"],
            "Hypertension": ["hypertension", "blood pressure", "cardiovascular", "hypertensive", "BP", "cardiac"],
            "Multiple Sclerosis": ["multiple sclerosis", "MS", "neurological", "autoimmune", "demyelinating", "neurodegenerative"]
        }

        # Get keywords for this condition
        keywords = condition_keywords.get(condition, [])
        if not keywords:
            # Generic fallback based on condition name
            keywords = [word.lower() for word in condition.split()]

        # Score articles by keyword relevance
        scored_articles = []
        for article in articles:
            title_text = str(article.get("title", "") or "").lower()
            article_text = (article.get("article_text", "") + "\n" + title_text).lower()

            if condition == "Breast Cancer Stage II":
                # Require breast context in the TITLE to avoid papers that only mention breast cancer in passing.
                if not any(term in title_text for term in ("breast cancer", "breast carcinoma", "mammary")):
                    continue
                required_any = (
                    "stage ii",
                    "early stage",
                    "early-stage",
                    "adjuvant",
                    "neoadjuvant",
                    "sentinel",
                    "radiotherapy",
                    "endocrine",
                    "tamoxifen",
                    "aromatase",
                    "her2",
                    "trastuzumab",
                    "pertuzumab",
                    "triple negative",
                    "tnbc",
                    "ductal",
                    "lobular",
                    "estrogen receptor",
                    "progesterone receptor",
                    "brca",
                )
                # Prefer early-stage/treatment-focused breast papers, but don't exclude all breast papers if missing.
                if any(term in article_text for term in required_any):
                    score_boost = 5
                else:
                    score_boost = 0

                excluded_any = (
                    "glioblastoma",
                    "colorectal",
                    "lung adenocarcinoma",
                    "gonorrhea",
                    "hiv-1",
                    "psychosis",
                )
                if any(term in article_text for term in excluded_any):
                    continue

            score = sum(1 for keyword in keywords if keyword.lower() in article_text)
            if condition == "Breast Cancer Stage II":
                score += score_boost

            if score > 0:
                scored_articles.append((score, article))

        # Sort by score (highest first) and return top N
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        return [article for score, article in scored_articles[:max_articles]]

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
                l = line.strip()
                if not l:
                    tail_lines.append("")
                    continue
                if "orcid.org" in l.lower():
                    continue
                if l.lower().startswith("===="):
                    continue
                tail_lines.append(l)
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
            "  \"research_topic\": string,\n"
            "  \"summaries\": [string, string, string]\n"
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
        Run the Medical Research Summarization Agent.

        This agent:
        1. Loads articles from PubMedCentral.json
        2. Finds articles relevant to patient's condition
        3. Uses AI to create summaries of real research
        4. Returns patient-specific research insights

        Args:
            patient_id: Patient identifier
            patient_data: Patient information

        Returns:
            Dictionary with research topic and AI-generated summaries from real papers
        """
        try:
            condition = patient_data.get("condition", "Unknown")
            patient_age = patient_data.get("age", "Unknown")
            patient_name = patient_data.get("name", "Unknown")

            print("   Loading PubMed articles...")
            # Load PubMed articles
            articles = self._load_pubmed_articles()
            if not articles:
                print("   No PubMed articles found, using generic summaries")
                return self._generate_fallback_research(patient_data)

            print(f"   Searching {len(articles)} articles for: {condition}")
            # Find relevant articles
            relevant_articles = self._find_relevant_articles(condition, articles, max_articles=5)

            if not relevant_articles:
                print(f"   No relevant articles found for {condition}")
                return self._generate_fallback_research(patient_data)

            print(f"   Found {len(relevant_articles)} relevant articles")

            # Extract content from articles for AI to summarize
            article_contents = []
            for i, article in enumerate(relevant_articles):
                content = self._extract_article_summary(article.get("article_text", ""))
                if content:
                    article_contents.append(f"Article {i+1}:\n{content}")

            if not article_contents:
                print("   No usable article excerpts extracted")
                return self._generate_fallback_research(patient_data)

            # Use AI to create patient-specific summaries
            print("   Generating AI summaries from research papers...")
            research_topic, summaries = self._generate_clean_summaries_from_articles(
                patient_name=patient_name,
                patient_age=patient_age,
                condition=condition,
                article_contents=article_contents,
            )

            print(f"   Generated {len(summaries)} AI summaries from real research")

            return {
                "research_topic": research_topic,
                "summaries": summaries,
                "condition": condition,
                "patient_id": patient_id,
                "articles_analyzed": len(relevant_articles),
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
                f"Ongoing trials are investigating novel therapeutic approaches for {condition} management."
            ],
            "condition": condition,
            "patient_id": patient_data.get("id", ""),
            "articles_analyzed": 0
        }

    async def run_message_router(
        self, announcement: str, staff_directory: list[dict]
    ) -> dict:
        """
        Run the Message Board Routing Agent.

        Args:
            announcement: The announcement to route
            staff_directory: List of staff members with roles/specialties

        Returns:
            Dictionary with routing decisions
        """
        try:
            # Get prompt from catalog
            prompt_record = None
            if self.catalog:
                try:
                    prompt_record = self.catalog.find("prompt", name="message_router_agent")
                except Exception as e:
                    print(f"Could not load prompt from catalog: {e}")

            # Format staff directory
            staff_text = "\n".join([
                f"- {s.get('name', 'Unknown')}: {s.get('role', 'Unknown')}"
                for s in staff_directory
            ])

            prompt_vars = {
                "announcement": announcement,
                "staff_directory": staff_text
            }

            # Build prompt
            if prompt_record:
                system_content = prompt_record.get("agent_instructions", "")
                user_content = self._format_prompt(
                    prompt_record.get("content", ""), prompt_vars
                )
            else:
                # Fallback prompt
                system_content = "You are an intelligent message routing system."
                user_content = f"""
                Announcement: {announcement}

                Staff: {staff_text}

                Determine who should receive this message and the priority level.
                """

            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_content)
            ]

            # Run LLM
            response = self.llm.invoke(messages)
            analysis = response.content

            # Parse for routing (simplified)
            priority = "medium"
            recipients = []

            if "urgent" in analysis.lower():
                priority = "urgent"
            elif "high" in analysis.lower():
                priority = "high"
            elif "low" in analysis.lower():
                priority = "low"

            # Extract recipient names (basic parsing)
            for staff in staff_directory:
                if staff.get("name", "") in analysis:
                    recipients.append(staff.get("name", ""))

            route = {
                "id": str(uuid.uuid4()),
                "original_message": announcement,
                "routed_to": recipients,
                "priority": priority,
                "timestamp": "",
                "analysis": analysis
            }

            return {
                "routes": [route],
                "recipients": recipients,
                "priority": priority
            }

        except Exception as e:
            print(f"Error in message router: {e}")
            return {
                "error": str(e),
                "routes": [],
                "recipients": [],
                "priority": "medium"
            }

    async def run_questionnaire_summarizer(
        self,
        patient_id: str,
        patient_data: dict,
        questionnaire_responses: dict,
        appointment_date: str
    ) -> dict:
        """
        Run the Questionnaire Summarization Agent.

        Args:
            patient_id: Patient identifier
            patient_data: Patient information
            questionnaire_responses: Dictionary of Q&A
            appointment_date: Date of appointment

        Returns:
            Dictionary with summary and key points
        """
        try:
            # Get prompt from catalog
            prompt_record = None
            if self.catalog:
                try:
                    prompt_record = self.catalog.find(
                        "prompt", name="questionnaire_summarizer_agent"
                    )
                except Exception as e:
                    print(f"Could not load prompt from catalog: {e}")

            # Format questionnaire
            q_text = "\n".join([
                f"Q: {q}\nA: {a}" for q, a in questionnaire_responses.items()
            ])

            prompt_vars = {
                "patient_name": patient_data.get("name", "Unknown"),
                "patient_age": patient_data.get("age", "Unknown"),
                "patient_condition": patient_data.get("condition", "Unknown"),
                "appointment_date": appointment_date,
                "questionnaire_responses": q_text
            }

            # Build prompt
            if prompt_record:
                system_content = prompt_record.get("agent_instructions", "")
                user_content = self._format_prompt(
                    prompt_record.get("content", ""), prompt_vars
                )
            else:
                # Fallback prompt
                system_content = "You are a medical assistant summarizing questionnaires."
                user_content = f"""
                Patient: {prompt_vars['patient_name']}
                Condition: {prompt_vars['patient_condition']}
                Appointment: {appointment_date}

                Questionnaire:
                {q_text}

                Create a concise summary with 3-5 key points.
                """

            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_content)
            ]

            # Run LLM
            response = self.llm.invoke(messages)
            content = response.content

            # Parse summary and key points
            lines = [l.strip() for l in content.split("\n") if l.strip()]

            # Extract summary (first paragraph) and key points (bulleted items)
            summary_lines = []
            key_points = []

            for line in lines:
                if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                    key_points.append(line.lstrip("-*• "))
                else:
                    summary_lines.append(line)

            summary = " ".join(summary_lines) if summary_lines else content[:300]

            # Ensure we have some key points
            if not key_points:
                key_points = summary_lines[:5]

            return {
                "summary": summary,
                "key_points": key_points[:5],
                "patient_id": patient_id,
                "appointment_date": appointment_date
            }

        except Exception as e:
            print(f"Error in questionnaire summarizer: {e}")
            return {
                "error": str(e),
                "summary": "",
                "key_points": []
            }


# Global orchestrator instance
orchestrator = HealthcareAgentOrchestrator()
