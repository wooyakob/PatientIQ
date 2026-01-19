import agentc
import agentc_langgraph.agent
import langchain_core.messages
import langchain_core.runnables
import langchain_openai.chat_models
import typing


class State(agentc_langgraph.agent.State):
    """State for the doc notes search agent"""

    patient_id: typing.Optional[str]
    patient_name: typing.Optional[str]
    question: typing.Optional[str]
    notes: typing.Optional[list[dict]]
    answer: typing.Optional[str]
    is_complete: bool
    previous_node: typing.Optional[str]
    is_last_step: bool


class DocNotesSearchAgent(agentc_langgraph.agent.ReActAgent):
    """
    Agent for searching doctor notes and answering questions about past visits.

    Uses the docnotes_search_agent prompt and doc_notes_search tool from the catalog.
    """

    def __init__(self, catalog: agentc.Catalog, span: agentc.Span):
        chat_model = langchain_openai.chat_models.ChatOpenAI(model="gpt-4o-mini", temperature=0)
        super().__init__(
            chat_model=chat_model, catalog=catalog, span=span, prompt_name="docnotes_search_agent"
        )

    def _invoke(
        self, span: agentc.Span, state: State, config: langchain_core.runnables.RunnableConfig
    ) -> State:
        """
        Execute the doc notes search workflow.

        Args:
            span: Tracing span for observability
            state: Current state with patient_id and question
            config: LangGraph configuration

        Returns:
            Updated state with search results
        """
        # Create the agent and invoke it
        agent = self.create_react_agent(span)
        response = agent.invoke(input=state, config=config)

        # Extract structured response from the prompt output schema
        structured_response = response.get("structured_response", {})

        # Update state with search results
        state["patient_id"] = structured_response.get("patient_id", state.get("patient_id"))
        state["patient_name"] = structured_response.get("patient_name")
        state["question"] = structured_response.get("question", state.get("question"))
        state["notes"] = structured_response.get("notes", [])
        state["answer"] = structured_response.get("answer")
        state["is_complete"] = True

        # Append the AI response to messages
        if response.get("messages"):
            state["messages"].append(response["messages"][-1])

        return state
