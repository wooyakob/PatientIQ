import argparse
import json
import os
import pathlib
import sys
import typing

import agentc
import langchain_core.messages


def _load_agent_graph_class(agent_name: str, class_name: str):
    agent_dir = pathlib.Path(__file__).resolve().parents[2] / "agents" / agent_name
    module_path = agent_dir / "graph.py"

    unique_module_name = f"eval_{agent_name}_graph"

    import importlib.util

    spec = importlib.util.spec_from_file_location(unique_module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load agent module spec from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_module_name] = module

    original_sys_path = list(sys.path)
    if str(agent_dir) not in sys.path:
        sys.path.insert(0, str(agent_dir))

    try:
        spec.loader.exec_module(module)
    finally:
        sys.path = original_sys_path

    try:
        return getattr(module, class_name)
    except Exception as e:
        raise RuntimeError(f"Unable to load {class_name} from {module_path}") from e


def _try_build_scorer():
    try:
        import langchain_openai
        import ragas.llms
        import ragas.metrics
    except Exception:
        return None

    evaluator_llm = ragas.llms.LangchainLLMWrapper(
        langchain_openai.chat_models.ChatOpenAI(model="gpt-4o", temperature=0)
    )
    return ragas.metrics.SimpleCriteriaScore(
        name="coarse_grained_score",
        llm=evaluator_llm,
        definition="Score 0 to 5 by similarity.",
    )


def _read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _score_if_possible(scorer, user_content: str, ai_content: str, reference: str):
    if scorer is None:
        return None
    if reference is None:
        return None
    try:
        import ragas
        import ragas.messages

        sample = ragas.MultiTurnSample(
            user_input=[
                ragas.messages.HumanMessage(content=user_content),
                ragas.messages.AIMessage(content=ai_content),
            ],
            reference=reference,
        )
        return scorer.multi_turn_score(sample)
    except Exception:
        return None


def _run_pulmonary_research_suite(
    catalog: agentc.Catalog,
    root_span: agentc.Span,
    scorer,
    resource_path: pathlib.Path,
):
    PulmonaryResearcher = _load_agent_graph_class("pulmonary_research_agent", "PulmonaryResearcher")

    with root_span.new("PulmonaryResearchAgent") as suite_span:
        for i, row in enumerate(_read_jsonl(resource_path)):
            test_input = row.get("input") or {}
            patient_id = test_input.get("patient_id")
            question = test_input.get("question")
            reference = row.get("reference")

            with suite_span.new(f"Eval_{i}", test_input=json.dumps(row)) as eval_span:
                state = PulmonaryResearcher.build_starting_state(
                    patient_id=patient_id, question=question
                )

                user_message = json.dumps(
                    {"patient_id": str(patient_id or ""), "question": str(question or "")}
                )
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                try:
                    eval_span["ran"] = True
                    result = PulmonaryResearcher(catalog=catalog, span=eval_span).invoke(
                        input=state
                    )
                    eval_span["is_last_step"] = bool(result.get("is_last_step"))
                    eval_span["is_complete"] = bool(result.get("is_complete"))
                    eval_span["papers_count"] = len(result.get("papers") or [])

                    answer = str(result.get("answer") or "")
                    eval_span["answer_len"] = len(answer)

                    score = _score_if_possible(scorer, user_message, answer, reference)
                    if score is not None:
                        eval_span["goal_accuracy"] = {"score": score, "reference": reference}
                except Exception as e:
                    eval_span["ran"] = False
                    eval_span["error"] = str(e)


def _run_docnotes_search_suite(
    catalog: agentc.Catalog,
    root_span: agentc.Span,
    scorer,
    resource_path: pathlib.Path,
):
    DocNotesSearcher = _load_agent_graph_class("docnotes_search_agent", "DocNotesSearcher")

    with root_span.new("DocNotesSearchAgent") as suite_span:
        for i, row in enumerate(_read_jsonl(resource_path)):
            test_input = row.get("input") or {}
            patient_id = test_input.get("patient_id")
            patient_name = test_input.get("patient_name")
            question = test_input.get("question")
            reference = row.get("reference")

            with suite_span.new(f"Eval_{i}", test_input=json.dumps(row)) as eval_span:
                state = DocNotesSearcher.build_starting_state(
                    patient_id=patient_id, question=question
                )
                if patient_name is not None:
                    state["patient_name"] = patient_name

                user_message = json.dumps(
                    {
                        "patient_id": str(patient_id or ""),
                        "patient_name": str(patient_name or ""),
                        "question": str(question or ""),
                    }
                )
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                try:
                    eval_span["ran"] = True
                    result = DocNotesSearcher(catalog=catalog, span=eval_span).invoke(input=state)
                    eval_span["is_last_step"] = bool(result.get("is_last_step"))
                    eval_span["is_complete"] = bool(result.get("is_complete"))
                    eval_span["notes_count"] = len(result.get("notes") or [])

                    answer = str(result.get("answer") or "")
                    eval_span["answer_len"] = len(answer)

                    score = _score_if_possible(scorer, user_message, answer, reference)
                    if score is not None:
                        eval_span["goal_accuracy"] = {"score": score, "reference": reference}
                except Exception as e:
                    eval_span["ran"] = False
                    eval_span["error"] = str(e)


def _run_previsit_summary_suite(
    catalog: agentc.Catalog,
    root_span: agentc.Span,
    scorer,
    resource_path: pathlib.Path,
):
    PrevisitSummarizer = _load_agent_graph_class("previsit_summary_agent", "PrevisitSummarizer")

    with root_span.new("PrevisitSummaryAgent") as suite_span:
        for i, row in enumerate(_read_jsonl(resource_path)):
            test_input = row.get("input") or {}
            patient_id = test_input.get("patient_id")
            reference = row.get("reference")

            with suite_span.new(f"Eval_{i}", test_input=json.dumps(row)) as eval_span:
                state = PrevisitSummarizer.build_starting_state(patient_id=patient_id)

                user_message = json.dumps({"patient_id": str(patient_id or "")})
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                try:
                    eval_span["ran"] = True
                    result = PrevisitSummarizer(catalog=catalog, span=eval_span).invoke(input=state)
                    eval_span["is_last_step"] = bool(result.get("is_last_step"))
                    eval_span["is_complete"] = bool(result.get("is_complete"))

                    summary = str(result.get("clinical_summary") or "")
                    eval_span["clinical_summary_len"] = len(summary)

                    score = _score_if_possible(scorer, user_message, summary, reference)
                    if score is not None:
                        eval_span["goal_accuracy"] = {"score": score, "reference": reference}
                except Exception as e:
                    eval_span["ran"] = False
                    eval_span["error"] = str(e)


def main(argv: typing.Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite",
        action="append",
        choices=["pulmonary", "docnotes", "previsit"],
        default=None,
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    suites = args.suite or ["pulmonary", "docnotes", "previsit"]

    project_root = pathlib.Path(__file__).resolve().parents[2]
    resources_dir = project_root / "tests" / "evals" / "resources"

    catalog = agentc.Catalog()
    root_span = catalog.Span(name="agent_evals")

    scorer = None
    if (os.getenv("ENABLE_RAGAS") or "").strip().lower() in {"1", "true", "yes"}:
        scorer = _try_build_scorer()

    if "pulmonary" in suites:
        _run_pulmonary_research_suite(
            catalog=catalog,
            root_span=root_span,
            scorer=scorer,
            resource_path=resources_dir / "pulmonary_research.jsonl",
        )

    if "docnotes" in suites:
        _run_docnotes_search_suite(
            catalog=catalog,
            root_span=root_span,
            scorer=scorer,
            resource_path=resources_dir / "docnotes_search.jsonl",
        )

    if "previsit" in suites:
        _run_previsit_summary_suite(
            catalog=catalog,
            root_span=root_span,
            scorer=scorer,
            resource_path=resources_dir / "previsit_summary.jsonl",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
