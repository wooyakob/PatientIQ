import langgraph.graph
import node
import typing


def _edge(state: node.State) -> typing.Literal["_agent", "_agent", "__end__"]:
    if state["is_last_step"]:
        return langgraph.graph.END
    elif state["needs_clarification"]:
        return "_agent"
    else:
        return "_agent"


def _edge(state: node.State) -> typing.Literal["_agent", "_agent"]:
    if state[""] or state["is_last_step"]:
        return "_agent"
    else:
        return "_agent"
