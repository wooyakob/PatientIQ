"""
Wearable Analytics Agent - Graph Definition

ARCHITECTURE:
============

    API Request
        ↓
    ┌─────────────────────────────────────┐
    │  Graph (this file)                  │
    │  • build_starting_state()           │
    │  • compile() workflow               │
    └─────────┬───────────────────────────┘
              ↓
    ┌─────────────────────────────────────┐
    │  Node (node.py)                     │
    │  • WearableAnalyticsAgent           │
    │  • _invoke() - does the work        │
    │  • Calls tools via ReAct loop       │
    └─────────┬───────────────────────────┘
              ↓
    ┌─────────────────────────────────────┐
    │  Edge (edge.py)                     │
    │  • out_analytics_agent_edge()       │
    │  • Decides: continue or END         │
    └─────────┬───────────────────────────┘
              ↓
         END → Return results to API

STATE FLOW:
===========
Input:  {patient_id: "1", question: "...", is_complete: False}
        ↓ [node processes]
Output: {patient_id: "1", alerts: [...], answer: "...", is_complete: True}

TOOLS USED (defined in prompt YAML):
=====================================
• get_wearable_data_by_patient  - Retrieve wearable metrics
• find_similar_patients_demographics - Find similar patients
• analyze_wearable_trends - Statistical analysis & alerts
• compare_patient_to_cohort - Percentile rankings
• hybrid_search_research_papers - Research papers (RAG)
"""

import agentc_langgraph.graph
import dotenv
import langgraph.graph
import importlib.util
from pathlib import Path

# Import edge and node modules from this directory specifically
_current_dir = Path(__file__).parent

edge_spec = importlib.util.spec_from_file_location("wearable_analytics_edge", _current_dir / "edge.py")
edge_module = importlib.util.module_from_spec(edge_spec)
edge_spec.loader.exec_module(edge_module)
out_analytics_agent_edge = edge_module.out_analytics_agent_edge

node_spec = importlib.util.spec_from_file_location("wearable_analytics_node", _current_dir / "node.py")
node_module = importlib.util.module_from_spec(node_spec)
node_spec.loader.exec_module(node_module)
WearableAnalyticsAgent = node_module.WearableAnalyticsAgent
State = node_module.State

# Make sure you populate your .env file with the correct credentials!
dotenv.load_dotenv()


class WearableAnalyzer(agentc_langgraph.graph.GraphRunnable):
    """
    LangGraph workflow for analyzing wearable data.

    This agent:
    1. Takes a patient_id and optional question
    2. Retrieves wearable data for the patient
    3. Analyzes trends and generates alerts
    4. Finds similar patients for demographic comparison
    5. Compares patient to cohort averages
    6. Connects symptoms to relevant research papers
    7. Provides clinical recommendations based on all findings
    """

    @staticmethod
    def build_starting_state(
        patient_id: str = None, 
        question: str = None,
        days: int = 30
    ) -> State:
        """
        Build the initial state for the analytics workflow.

        Args:
            patient_id: Patient ID to analyze
            question: Optional specific question about wearable data
            days: Number of days of wearable data to analyze (default: 30)

        Returns:
            Initial state with empty messages and analysis fields
        """
        return State(
            messages=[],
            patient_id=patient_id,
            patient_name=None,
            patient_condition=None,
            question=question or f"Analyze wearable data for the last {days} days",
            wearable_data=None,
            similar_patients=None,
            trend_analysis=None,
            cohort_comparison=None,
            research_papers=None,
            alerts=None,
            recommendations=None,
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
        # Build our analytics agent node
        analytics_agent = WearableAnalyticsAgent(
            catalog=self.catalog,
            span=self.span,
        )

        # Create a workflow graph
        workflow = langgraph.graph.StateGraph(State)
        workflow.add_node("analytics_agent", analytics_agent)
        workflow.set_entry_point("analytics_agent")
        workflow.add_conditional_edges(
            "analytics_agent",
            out_analytics_agent_edge,
        )

        return workflow.compile()
