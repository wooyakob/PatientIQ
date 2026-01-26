import agentc_langgraph.graph
import dotenv
import langgraph.graph

from previsit_edge import out_summary_agent_edge
from previsit_node import PrevisitSummaryAgent
from previsit_node import State

dotenv.load_dotenv()


class PrevisitSummarizer(agentc_langgraph.graph.GraphRunnable):
    """
    LangGraph workflow for generating pre-visit clinical summaries.

    This agent:
    1. Takes a patient_id as input
    2. Retrieves patient information, questionnaire data, and recent notes
    3. Generates a structured clinical summary using GPT-4o-mini
    4. Returns formatted data for physician review including medications, allergies, symptoms, and concerns
    """

    @staticmethod
    def build_starting_state(patient_id: str = None) -> State:
        """
        Build the initial state for the pre-visit summary workflow.

        Args:
            patient_id: Patient ID to generate summary for

        Returns:
            Initial state with empty fields
        """
        return State(
            messages=[],
            patient_id=patient_id,
            patient_name=None,
            clinical_summary=None,
            current_medications=None,
            allergies=None,
            key_symptoms=None,
            patient_concerns=None,
            recent_note_summary=None,
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
        # Build our summary agent node
        summary_agent = PrevisitSummaryAgent(
            catalog=self.catalog,
            span=self.span,
        )

        # Create a workflow graph
        workflow = langgraph.graph.StateGraph(State)
        workflow.add_node("summary_agent", summary_agent)
        workflow.set_entry_point("summary_agent")
        workflow.add_conditional_edges(
            "summary_agent",
            out_summary_agent_edge,
        )

        return workflow.compile()
