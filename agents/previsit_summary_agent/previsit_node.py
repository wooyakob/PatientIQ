import agentc
import agentc_langgraph.agent
import langchain_core.runnables
import langchain_openai.chat_models
import os
import typing


class State(agentc_langgraph.agent.State):
    """State for the pre-visit summary agent"""

    patient_id: typing.Optional[str]
    patient_name: typing.Optional[str]
    clinical_summary: typing.Optional[str]
    current_medications: typing.Optional[list[dict]]
    allergies: typing.Optional[dict]
    key_symptoms: typing.Optional[list[str]]
    patient_concerns: typing.Optional[list[str]]
    recent_note_summary: typing.Optional[str]
    is_complete: bool
    previous_node: typing.Optional[str]
    is_last_step: bool


class PrevisitSummaryAgent(agentc_langgraph.agent.ReActAgent):
    """
    Agent for generating pre-visit summaries for doctors.

    Uses OpenAI's GPT-4o-mini with the ReAct pattern to:
    1. Call tools to gather patient data, questionnaire responses, and recent notes
    2. Generate a structured clinical summary for the physician
    """

    def __init__(self, catalog: agentc.Catalog, span: agentc.Span):
        chat_model = langchain_openai.chat_models.ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
        )
        super().__init__(
            chat_model=chat_model,
            catalog=catalog,
            span=span,
            prompt_name="previsit_summarizer_agent",
        )

    def _invoke(
        self,
        span: agentc.Span,
        state: State,
        config: langchain_core.runnables.RunnableConfig,
    ) -> State:
        """
        Execute the pre-visit summary workflow.

        The agent calls three tools to gather data:
        1. find_patient_by_id - Gets patient demographics and conditions
        2. get_previsit_questionnaire - Gets patient-reported symptoms and concerns
        3. docnotes_latest_by_patient_id - Gets most recent clinical note

        Then generates a structured summary for the physician.

        Args:
            span: Tracing span for observability
            state: Current state with patient_id
            config: LangGraph configuration

        Returns:
            Updated state with summary and structured data
        """
        span.log(
            agentc.span.SystemContent(
                value=f"Starting pre-visit summary for patient {state.get('patient_id')}"
            )
        )

        # Create ReAct agent and set recursion limit to prevent infinite loops
        agent = self.create_react_agent(span)
        config = (
            {"recursion_limit": 15}
            if not isinstance(config, dict)
            else {**config, "recursion_limit": 15}
        )

        # Invoke agent to gather data and generate structured response
        response = agent.invoke(input=state, config=config)
        structured_response = response.get("structured_response", {})

        # Update state with extracted data
        state.update(
            {
                "patient_id": structured_response.get("patient_id", state.get("patient_id")),
                "patient_name": structured_response.get("patient_name"),
                "clinical_summary": structured_response.get("clinical_summary", ""),
                "current_medications": structured_response.get("current_medications", []),
                "allergies": structured_response.get(
                    "allergies", {"drug": [], "food": [], "environmental": []}
                ),
                "key_symptoms": structured_response.get("key_symptoms", []),
                "patient_concerns": structured_response.get("patient_concerns", []),
                "recent_note_summary": structured_response.get("recent_note_summary", ""),
                "is_complete": True,
                "is_last_step": True,
            }
        )

        # Append AI response to message history
        if response.get("messages"):
            state["messages"].append(response["messages"][-1])

        span.log(
            agentc.span.SystemContent(
                value=f"Pre-visit summary complete for {state.get('patient_name')}"
            )
        )

        return state
