import agentc
import agentc_langgraph.agent
import langchain_core.messages
import langchain_core.runnables
import langchain_openai.chat_models
import typing


class State(agentc_langgraph.agent.State):
    """State for the pulmonary research agent"""
    patient_id: typing.Optional[str]
    patient_name: typing.Optional[str]
    condition: typing.Optional[str]
    question: typing.Optional[str]
    papers: typing.Optional[list[dict]]
    answer: typing.Optional[str]
    is_complete: bool
    previous_node: typing.Optional[str]
    is_last_step: bool


class PulmonaryResearchAgent(agentc_langgraph.agent.ReActAgent):
    """
    Agent for researching pulmonary conditions and summarizing medical research.

    Uses the pulmonary_research_agent prompt and paper_search tool from the catalog.
    """

    def __init__(self, catalog: agentc.Catalog, span: agentc.Span):
        chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o-mini", temperature=0)
        super().__init__(
            chat_model=chat_model,
            catalog=catalog,
            span=span,
            prompt_name="pulmonary_research_agent"
        )

    def _invoke(
        self,
        span: agentc.Span,
        state: State,
        config: langchain_core.runnables.RunnableConfig
    ) -> State:
        """
        Execute the pulmonary research workflow.

        Args:
            span: Tracing span for observability
            state: Current state with patient_id and question
            config: LangGraph configuration

        Returns:
            Updated state with research results
        """
        span.log(agentc.span.SystemContent(
            value=f"Starting pulmonary research for patient {state.get('patient_id')}"
        ))

        # Create the agent and invoke it
        agent = self.create_react_agent(span)
        response = agent.invoke(input=state, config=config)

        # Extract structured response from the prompt output schema
        structured_response = response.get("structured_response", {})

        # Update state with research results
        state["patient_id"] = structured_response.get("patient_id", state.get("patient_id"))
        state["patient_name"] = structured_response.get("patient_name")
        state["condition"] = structured_response.get("condition")
        state["question"] = structured_response.get("question", state.get("question"))
        state["papers"] = structured_response.get("papers", [])
        state["answer"] = structured_response.get("answer")
        state["is_complete"] = True

        # Append the AI response to messages
        if response.get("messages"):
            state["messages"].append(response["messages"][-1])

        span.log(agentc.span.SystemContent(
            value=f"Research complete: {len(state['papers'])} papers found"
        ))

        return state
