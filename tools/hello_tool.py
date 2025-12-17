import agentc


@agentc.catalog.tool
def hello_tool(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"
