import langgraph.graph
import node
import typing


def out_search_agent_edge(
    state: node.State
) -> typing.Literal["__end__"]:
    """
    Routing logic after the doc notes search agent completes.

    Since this is a single-agent workflow, we always end after search is complete.

    Args:
        state: Current state of the agent

    Returns:
        Always returns END to finish the workflow
    """
    if state.get("is_complete"):
        return langgraph.graph.END
    return langgraph.graph.END
