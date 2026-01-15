import agentc_langgraph.graph
import dotenv
import langgraph.graph

from edge import out_research_agent_edge
from node import PulmonaryResearchAgent
from node import State

# Make sure you populate your .env file with the correct credentials!
dotenv.load_dotenv()


class PulmonaryResearcher(agentc_langgraph.graph.GraphRunnable):
    """
    LangGraph workflow for pulmonary medical research.

    This agent:
    1. Takes a patient_id and clinical question
    2. Retrieves the patient's pulmonary condition
    3. Searches for relevant medical research papers
    4. Generates a concise clinical summary for the doctor
    """

    @staticmethod
    def build_starting_state(patient_id: str = None, question: str = None) -> State:
        """
        Build the initial state for the research workflow.

        Args:
            patient_id: Optional patient ID to research
            question: Optional clinical question from the doctor

        Returns:
            Initial state with empty messages and research fields
        """
        return State(
            messages=[],
            patient_id=patient_id,
            patient_name=None,
            condition=None,
            question=question,
            papers=None,
            answer=None,
            is_complete=False,
            previous_node=None,
            is_last_step=False
        )

    def compile(self) -> langgraph.graph.StateGraph:
        """
        Compile the agent workflow graph.

        Returns:
            Compiled LangGraph StateGraph
        """
        # Build our research agent node
        research_agent = PulmonaryResearchAgent(
            catalog=self.catalog,
            span=self.span,
        )

        # Create a workflow graph
        workflow = langgraph.graph.StateGraph(State)
        workflow.add_node("research_agent", research_agent)
        workflow.set_entry_point("research_agent")
        workflow.add_conditional_edges(
            "research_agent",
            out_research_agent_edge,
        )

        return workflow.compile()
