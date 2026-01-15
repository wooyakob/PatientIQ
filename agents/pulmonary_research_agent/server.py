import agentc
import agentc_langgraph.state
import fastapi
import langchain_core.messages
import pydantic
import starlette.responses

from graph import PulmonaryResearcher

app = fastapi.FastAPI()

# The following is shared across sessions for a single worker.
catalog = agentc.Catalog()
checkpointer = agentc_langgraph.state.CheckpointSaver(create_if_not_exists=True)
span = catalog.Span(name="PulmonaryResearchAPI")
researcher = PulmonaryResearcher(catalog=catalog, span=span)


class ResearchRequest(pydantic.BaseModel):
    """Request model for pulmonary research endpoint"""
    session_id: str
    patient_id: str
    question: str
    enable_tracing: bool = True


class ResearchResponse(pydantic.BaseModel):
    """Response model for pulmonary research endpoint"""
    patient_id: str
    patient_name: str | None
    condition: str | None
    question: str
    papers: list[dict]
    answer: str | None
    error: str | None = None


@app.post("/research", response_model=ResearchResponse)
async def research(req: ResearchRequest):
    """
    Perform pulmonary research for a patient's condition.

    Args:
        req: Research request with patient_id and clinical question

    Returns:
        Research results with papers and clinical summary
    """
    try:
        # Build starting state
        input_state = PulmonaryResearcher.build_starting_state(
            patient_id=req.patient_id,
            question=req.question
        )

        # Add the question as a human message
        input_state["messages"].append(
            langchain_core.messages.HumanMessage(
                content=f'{{"patient_id": "{req.patient_id}", "question": "{req.question}"}}'
            )
        )

        # Configure session
        config = {"configurable": {"thread_id": f"{req.patient_id}/{req.session_id}"}}

        # Invoke the agent
        result = researcher.invoke(input=input_state, config=config)

        # Build response
        return ResearchResponse(
            patient_id=result.get("patient_id", req.patient_id),
            patient_name=result.get("patient_name"),
            condition=result.get("condition"),
            question=result.get("question", req.question),
            papers=result.get("papers", []),
            answer=result.get("answer"),
            error=None
        )

    except Exception as e:
        return ResearchResponse(
            patient_id=req.patient_id,
            patient_name=None,
            condition=None,
            question=req.question,
            papers=[],
            answer=None,
            error=str(e)
        )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pulmonary-research-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
