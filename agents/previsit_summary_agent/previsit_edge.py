import langgraph.graph

from previsit_node import State


def out_summary_agent_edge(state: State) -> str:
    """
    Determine the next node after the summary agent completes.

    Since the pre-visit summary agent completes in a single step,
    this always returns END.

    Args:
        state: Current state

    Returns:
        langgraph.graph.END
    """
    return langgraph.graph.END
