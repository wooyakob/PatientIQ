import agentc
import agentc_langgraph.agent
import json
import langchain_core.messages
import langchain_core.runnables
import langchain_openai.chat_models
import typing


def _coerce_tool_result_to_papers(value: typing.Any) -> typing.Optional[list[dict]]:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(x, dict) for x in value):
        return typing.cast(list[dict], value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            parsed = json.loads(s)
        except Exception:
            return None
        if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
            return typing.cast(list[dict], parsed)
        return None
    return None


def _extract_paper_search_papers(response: dict) -> typing.Optional[list[dict]]:
    """Attempt to extract the paper_search tool output from an agent invoke response."""

    intermediate_steps = response.get("intermediate_steps")
    if isinstance(intermediate_steps, list):
        for step in reversed(intermediate_steps):
            if not (isinstance(step, (list, tuple)) and len(step) >= 2):
                continue
            action, observation = step[0], step[1]
            tool_name = getattr(action, "tool", None) or getattr(action, "tool_name", None)
            if tool_name == "paper_search":
                papers = _coerce_tool_result_to_papers(observation)
                if papers is not None:
                    return papers

    messages = response.get("messages")
    if isinstance(messages, list):
        for m in reversed(messages):
            name = getattr(m, "name", None)
            m_type = getattr(m, "type", None)
            if name == "paper_search" or m_type == "tool" and name == "paper_search":
                papers = _coerce_tool_result_to_papers(getattr(m, "content", None))
                if papers is not None:
                    return papers

    tool_results = response.get("tool_results")
    if isinstance(tool_results, dict) and "paper_search" in tool_results:
        papers = _coerce_tool_result_to_papers(tool_results.get("paper_search"))
        if papers is not None:
            return papers

    return None


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
        super().__init__(chat_model=chat_model, catalog=catalog, span=span, prompt_name="pulmonary_research_agent")

    def _invoke(self, span: agentc.Span, state: State, config: langchain_core.runnables.RunnableConfig) -> State:
        """
        Execute the pulmonary research workflow.

        Args:
            span: Tracing span for observability
            state: Current state with patient_id and question
            config: LangGraph configuration

        Returns:
            Updated state with research results
        """
        # Create the agent and invoke it
        agent = self.create_react_agent(span)
        response = agent.invoke(input=state, config=config)

        # Extract structured response from the prompt output schema
        structured_response = response.get("structured_response", {})

        tool_papers = None
        if isinstance(response, dict):
            tool_papers = _extract_paper_search_papers(response)

        # Update state with research results
        state["patient_id"] = structured_response.get("patient_id", state.get("patient_id"))
        state["patient_name"] = structured_response.get("patient_name")
        state["condition"] = structured_response.get("condition")
        state["question"] = structured_response.get("question", state.get("question"))
        # ONLY use papers from the paper_search tool - never use LLM-generated papers from structured_response
        state["papers"] = tool_papers if tool_papers is not None else []
        state["answer"] = structured_response.get("answer")
        state["is_complete"] = True

        # Append the AI response to messages
        if response.get("messages"):
            state["messages"].append(response["messages"][-1])

        return state
