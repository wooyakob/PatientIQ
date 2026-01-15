import agentc_langgraph.graph
import dotenv
import langgraph.graph
import importlib.util
from pathlib import Path

# Import edge and node modules from this directory specifically
_current_dir = Path(__file__).parent

edge_spec = importlib.util.spec_from_file_location("docnotes_edge", _current_dir / "edge.py")
edge_module = importlib.util.module_from_spec(edge_spec)
edge_spec.loader.exec_module(edge_module)
out_search_agent_edge = edge_module.out_search_agent_edge

node_spec = importlib.util.spec_from_file_location("docnotes_node", _current_dir / "node.py")
node_module = importlib.util.module_from_spec(node_spec)
node_spec.loader.exec_module(node_module)
DocNotesSearchAgent = node_module.DocNotesSearchAgent
State = node_module.State

# Make sure you populate your .env file with the correct credentials!
dotenv.load_dotenv()


class DocNotesSearcher(agentc_langgraph.graph.GraphRunnable):
    """
    LangGraph workflow for searching doctor notes.

    This agent:
    1. Takes a patient_id and a question
    2. Retrieves the patient's name
    3. Searches doctor notes using semantic vector search
    4. Generates a concise answer based on the notes
    """

    @staticmethod
    def build_starting_state(patient_id: str = None, question: str = None) -> State:
        """
        Build the initial state for the search workflow.

        Args:
            patient_id: Optional patient ID
            question: Optional question about past visits

        Returns:
            Initial state with empty messages and search fields
        """
        return State(
            messages=[],
            patient_id=patient_id,
            patient_name=None,
            question=question,
            notes=None,
            answer=None,
            is_complete=False,
            previous_node=None,
            is_last_step=False,
        )

    def compile(self) -> langgraph.graph.StateGraph:
        """
        Compile the agent workflow graph.

        Returns:
            Compiled LangGraph StateGraph
        """
        # Build our search agent node
        search_agent = DocNotesSearchAgent(
            catalog=self.catalog,
            span=self.span,
        )

        # Create a workflow graph
        workflow = langgraph.graph.StateGraph(State)
        workflow.add_node("search_agent", search_agent)
        workflow.set_entry_point("search_agent")
        workflow.add_conditional_edges(
            "search_agent",
            out_search_agent_edge,
        )

        return workflow.compile()
