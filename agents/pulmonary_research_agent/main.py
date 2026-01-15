#!/usr/bin/env python3
"""
Pulmonary Research Agent - CLI Interface

A medical research agent that:
- Retrieves patient pulmonary conditions from Couchbase
- Searches medical research papers using vector search
- Generates concise clinical summaries for doctors

Uses:
- Couchbase Agent Catalog for tool and prompt management
- LangGraph for agent workflow orchestration
- Agent Tracer for observability
"""

if __name__ == "__main__":
    import agentc
    import graph
    import langchain_core.messages

    print("=" * 70)
    print("Pulmonary Research Agent - CLI Interface")
    print("=" * 70)
    print()

    # Initialize the Agent Catalog
    catalog = agentc.Catalog()

    # Get patient ID and question from user
    patient_id = input("Enter patient ID (default: 1): ").strip() or "1"
    question = input("Enter clinical question (default: treatment options): ").strip() or \
               "What are evidence-based treatment options for this patient's condition?"

    print()
    print("=" * 70)
    print("Starting Research...")
    print("=" * 70)
    print()

    # Build starting state
    state = graph.PulmonaryResearcher.build_starting_state(
        patient_id=patient_id,
        question=question
    )

    # Add the question as a human message in JSON format (as expected by the prompt)
    state["messages"].append(
        langchain_core.messages.HumanMessage(
            content=f'{{"patient_id": "{patient_id}", "question": "{question}"}}'
        )
    )

    # Run the agent
    result = graph.PulmonaryResearcher(catalog=catalog).invoke(input=state)

    # Display results
    print("\n" + "=" * 70)
    print("RESEARCH RESULTS")
    print("=" * 70)

    if result.get("patient_name"):
        print(f"\nPatient: {result['patient_name']} (ID: {result['patient_id']})")
    else:
        print(f"\nPatient ID: {result['patient_id']}")

    if result.get("condition"):
        print(f"Condition: {result['condition']}")

    print(f"Question: {result['question']}")

    papers = result.get("papers", [])
    print(f"\nFound {len(papers)} Relevant Papers:")
    print("-" * 70)

    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.get('title', 'No title')}")
        if paper.get("author"):
            print(f"   Author(s): {paper['author']}")
        if paper.get("article_citation"):
            print(f"   Citation: {paper['article_citation']}")
        if paper.get("pmc_link"):
            print(f"   Link: {paper['pmc_link']}")

    answer = result.get("answer")
    if answer:
        print("\nClinical Summary:")
        print("-" * 70)
        paragraphs = answer.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.strip():
                print(f"\n{paragraph.strip()}")

    print("\n" + "=" * 70)
    print("Research Complete!")
    print("=" * 70)
