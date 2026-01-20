import agentc
import agentc_langgraph.agent
import langchain_core.messages
import langchain_core.runnables
import langchain_openai.chat_models
import typing


class State(agentc_langgraph.agent.State):
    """State for the wearable analytics agent"""

    patient_id: typing.Optional[str]
    patient_name: typing.Optional[str]
    patient_condition: typing.Optional[str]
    question: typing.Optional[str]
    wearable_data: typing.Optional[list[dict]]
    similar_patients: typing.Optional[list[dict]]
    trend_analysis: typing.Optional[dict]
    cohort_comparison: typing.Optional[dict]
    research_papers: typing.Optional[list[dict]]
    alerts: typing.Optional[list[dict]]
    recommendations: typing.Optional[list[str]]
    answer: typing.Optional[str]
    is_complete: bool
    previous_node: typing.Optional[str]
    is_last_step: bool


class WearableAnalyticsAgent(agentc_langgraph.agent.ReActAgent):
    """
    Agent for analyzing wearable data and providing clinical insights.

    This agent:
    1. Retrieves patient wearable data
    2. Identifies concerning trends and generates alerts
    3. Finds demographically similar patients for comparison
    4. Compares patient metrics to cohort averages
    5. Connects observed symptoms to relevant research papers
    6. Provides evidence-based recommendations

    Uses the wearable_analytics_agent prompt and multiple analysis tools from the catalog.
    """

    def __init__(self, catalog: agentc.Catalog, span: agentc.Span):
        chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o", temperature=0)
        super().__init__(
            chat_model=chat_model, 
            catalog=catalog, 
            span=span, 
            prompt_name="wearable_analytics_agent"
        )

    def _invoke(
        self, span: agentc.Span, state: State, config: langchain_core.runnables.RunnableConfig
    ) -> State:
        """
        Execute the wearable analytics workflow.

        Args:
            span: Tracing span for observability
            state: Current state with patient_id and question
            config: LangGraph configuration

        Returns:
            Updated state with analysis results
        """
        span.log(
            agentc.span.SystemContent(
                value=f"Analyzing wearable data for patient {state.get('patient_id')}"
            )
        )

        # Create the agent and invoke it
        agent = self.create_react_agent(span)
        response = agent.invoke(input=state, config=config)

        # Extract structured response from the prompt output schema
        structured_response = response.get("structured_response", {})

        # Update state with analysis results
        state["patient_id"] = structured_response.get("patient_id", state.get("patient_id"))
        state["patient_name"] = structured_response.get("patient_name")
        state["patient_condition"] = structured_response.get("patient_condition")
        state["question"] = structured_response.get("question", state.get("question"))
        state["wearable_data"] = structured_response.get("wearable_data", [])
        state["similar_patients"] = structured_response.get("similar_patients", [])
        state["trend_analysis"] = structured_response.get("trend_analysis", {})
        state["cohort_comparison"] = structured_response.get("cohort_comparison", {})
        state["research_papers"] = structured_response.get("research_papers", [])
        state["alerts"] = structured_response.get("alerts", [])
        state["recommendations"] = structured_response.get("recommendations", [])
        state["answer"] = structured_response.get("answer")
        state["is_complete"] = True

        # Append the AI response to messages
        if response.get("messages"):
            state["messages"].append(response["messages"][-1])

        alert_count = len(state.get("alerts", []))
        span.log(
            agentc.span.SystemContent(
                value=f"Analysis complete: {alert_count} alerts detected"
            )
        )

        return state
