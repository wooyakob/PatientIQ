import langgraph.graph
import node
import typing


def out_research_agent_edge(state: node.State) -> typing.Literal["__end__"]:
    """
    Routing logic after the pulmonary research agent completes.

    Since this is a single-agent workflow, we always end after research is complete.

    Args:
        state: Current state of the agent

    Returns:
        Always returns END to finish the workflow
    """
    if state.get("is_complete"):
        return langgraph.graph.END
    return langgraph.graph.END
