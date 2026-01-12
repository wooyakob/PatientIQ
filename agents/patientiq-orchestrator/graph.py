import agentc_langgraph.graph
import dotenv
import langgraph.graph


from node import [name of]Agent
from node import State

# Make sure you populate your .env file with the correct credentials!
dotenv.load_dotenv()


class IQOrchestrator(agentc_langgraph.graph.GraphRunnable):
    @staticmethod
    def build_starting_state() -> State:
        return State(
            messages=[], needs_clarification=False, is_last_step=False, previous_node=None
        )

    def compile(self) -> langgraph.graph.StateGraph:
        # Build our nodes and agents.
       agent = Agent(
            catalog=self.catalog,
            span=self.span,
        )

        # Create a workflow graph.
        workflow = langgraph.graph.StateGraph(State)
        workflow.add_node("_agent", _agent)
        workflow.add_node()
        workflow.set_entry_point("_agent")
        workflow.add_conditional_edges(
            "_agent",
            _edge,
        )
        workflow.add_edge("_agent", "_agent")
        workflow.add_conditional_edges(
            "_agent",
            _edge,
        )
        return workflow.compile()
