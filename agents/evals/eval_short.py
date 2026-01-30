import agentc
import json
import dotenv
import os
import pathlib
import sys
import warnings
import contextlib


# Note: these evals should be run from the root of the project!
import langchain_core.messages


_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
dotenv.load_dotenv(_PROJECT_ROOT / ".env")


def _load_agent_graph_class(agent_name: str, class_name: str):
    agent_dir = _PROJECT_ROOT / "agents" / agent_name
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


# Our Agent Catalog objects (the same ones used for our application are used for tests as well).
# To denote that the following logs are associated with tests, we will name the Span after our test file.
catalog: agentc.Catalog = agentc.Catalog()

_enable_tracing = (os.getenv("ENABLE_TRACING") or "false").strip().lower() in {"1", "true", "yes"}

root_span: agentc.Span | None
if _enable_tracing:
    root_span = catalog.Span(name=pathlib.Path(__file__).stem)
else:
    root_span = None

_enable_ragas = (os.getenv("ENABLE_RAGAS") or "true").strip().lower() in {"1", "true", "yes"}

ragas = None
evaluator_llm = None
_scorers: dict[str, object] = {}

if _enable_ragas:
    try:
        import ragas
        import ragas.messages
        import ragas.metrics
        from openai import OpenAI
        from ragas.llms import llm_factory

        evaluator_llm = llm_factory("gpt-4o-mini", client=OpenAI())
    except Exception as e:
        error_text = str(e)
        if "OPENAI_API_KEY" in error_text or "api_key" in error_text:
            raise RuntimeError(
                "Ragas scoring is enabled but OPENAI_API_KEY is not set. "
                "Set OPENAI_API_KEY (or add it to .env) or run with ENABLE_RAGAS=false."
            ) from e
        raise RuntimeError(
            "Ragas scoring is enabled but could not be initialized. "
            "Install 'ragas' or run with ENABLE_RAGAS=false."
        ) from e


def _resources_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "resources"


def _get_scorer(name: str, definition: str):
    if ragas is None or evaluator_llm is None:
        return None
    cache_key = f"{name}::{definition}"
    if cache_key in _scorers:
        return _scorers[cache_key]

    scorer_obj = None
    try:
        from ragas.metrics.collections import SimpleCriteriaScore

        scorer_obj = SimpleCriteriaScore(name=name, llm=evaluator_llm, definition=definition)
    except Exception:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            scorer_obj = ragas.metrics.SimpleCriteriaScore(
                name=name,
                llm=evaluator_llm,
                definition=definition,
            )

    _scorers[cache_key] = scorer_obj
    return scorer_obj


def _score_criteria(
    criteria: dict[str, str], user_message: str, ai_message: str, reference: str
) -> dict[str, float]:
    if ragas is None or evaluator_llm is None:
        return {}

    ragas_input: list[ragas.messages.Message] = [
        ragas.messages.HumanMessage(content=user_message),
        ragas.messages.AIMessage(content=ai_message),
    ]
    sample = ragas.MultiTurnSample(user_input=ragas_input, reference=reference)

    out: dict[str, float] = {}
    for name, definition in criteria.items():
        scorer_obj = _get_scorer(name=name, definition=definition)
        if scorer_obj is None:
            continue
        score = scorer_obj.multi_turn_score(sample)
        try:
            out[name] = float(score)
        except Exception:
            continue
    return out


def eval_pulmonary_research():
    PulmonaryResearcher = _load_agent_graph_class("pulmonary_research_agent", "PulmonaryResearcher")
    total = 0
    is_last_step_ok = 0
    scored_cases = 0
    criteria_scores: dict[str, list[float]] = {}
    criteria = {
        "clinical_relevance": "Score 0 to 5 for how clinically relevant and responsive the answer is to the question and patient context.",
        "actionability": "Score 0 to 5 for actionable, practical next steps and clinical reasoning appropriate for a clinician.",
        "evidence_grounding": "Score 0 to 5 for grounding in evidence/guidelines and avoiding unsupported claims; penalize hallucinated citations.",
    }
    suite_ctx = (
        root_span.new("PulmonaryResearch")
        if root_span is not None
        else contextlib.nullcontext(None)
    )
    with (
        (_resources_dir() / "pulmonary_research.jsonl").open() as fp,
        suite_ctx as suite_span,
    ):
        for i, line in enumerate(fp):
            row = json.loads(line)
            reference = row.get("reference", "")
            _input = row.get("input", {})
            patient_id = _input.get("patient_id")
            question = _input.get("question")

            eval_ctx = (
                suite_span.new(f"Eval_{i}", test_input=line)
                if suite_span is not None
                else contextlib.nullcontext(None)
            )

            with eval_ctx as eval_span:
                graph = (
                    PulmonaryResearcher(catalog=catalog, span=eval_span)
                    if eval_span is not None
                    else PulmonaryResearcher(catalog=catalog)
                )
                state = PulmonaryResearcher.build_starting_state(
                    patient_id=patient_id, question=question
                )
                user_message = json.dumps({"patient_id": patient_id, "question": question})
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                result = graph.invoke(input=state)
                total += 1
                last_step = bool(result.get("is_last_step"))
                if last_step:
                    is_last_step_ok += 1
                if eval_span is not None:
                    eval_span["correctly_set_is_last_step"] = last_step

                answer = str(result.get("answer") or "")
                scores = _score_criteria(criteria, user_message, answer, reference)
                if scores:
                    scored_cases += 1
                    for k, v in scores.items():
                        criteria_scores.setdefault(k, []).append(v)
                    if eval_span is not None:
                        eval_span["quality"] = {"scores": scores, "reference": reference}

    criteria_avg = {k: (sum(v) / len(v)) for k, v in criteria_scores.items() if v}
    return {
        "suite": "PulmonaryResearch",
        "total": total,
        "is_last_step_ok": is_last_step_ok,
        "scored_cases": scored_cases,
        "criteria_avg": criteria_avg,
    }


def eval_docnotes_search():
    DocNotesSearcher = _load_agent_graph_class("docnotes_search_agent", "DocNotesSearcher")
    total = 0
    is_last_step_ok = 0
    scored_cases = 0
    criteria_scores: dict[str, list[float]] = {}
    criteria = {
        "answer_groundedness": "Score 0 to 5 for grounding: the answer should be supported by the available notes context and avoid hallucination.",
        "question_answering": "Score 0 to 5 for directly answering the user's question with the most important facts.",
        "uncertainty_handling": "Score 0 to 5 for appropriately stating uncertainty when data is missing and suggesting what to check next.",
    }
    suite_ctx = (
        root_span.new("DocNotesSearch") if root_span is not None else contextlib.nullcontext(None)
    )
    with (
        (_resources_dir() / "docnotes_search.jsonl").open() as fp,
        suite_ctx as suite_span,
    ):
        for i, line in enumerate(fp):
            row = json.loads(line)
            reference = row.get("reference", "")
            _input = row.get("input", {})
            patient_id = _input.get("patient_id")
            patient_name = _input.get("patient_name")
            question = _input.get("question")

            eval_ctx = (
                suite_span.new(f"Eval_{i}", test_input=line)
                if suite_span is not None
                else contextlib.nullcontext(None)
            )

            with eval_ctx as eval_span:
                graph = (
                    DocNotesSearcher(catalog=catalog, span=eval_span)
                    if eval_span is not None
                    else DocNotesSearcher(catalog=catalog)
                )
                state = DocNotesSearcher.build_starting_state(
                    patient_id=patient_id, question=question
                )
                if patient_name is not None:
                    state["patient_name"] = patient_name

                user_message = json.dumps(
                    {
                        "patient_id": patient_id,
                        "patient_name": patient_name or "",
                        "question": question,
                    }
                )
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                result = graph.invoke(input=state)
                total += 1
                last_step = bool(result.get("is_last_step"))
                if last_step:
                    is_last_step_ok += 1
                if eval_span is not None:
                    eval_span["correctly_set_is_last_step"] = last_step

                answer = str(result.get("answer") or "")
                scores = _score_criteria(criteria, user_message, answer, reference)
                if scores:
                    scored_cases += 1
                    for k, v in scores.items():
                        criteria_scores.setdefault(k, []).append(v)
                    if eval_span is not None:
                        eval_span["quality"] = {"scores": scores, "reference": reference}

    criteria_avg = {k: (sum(v) / len(v)) for k, v in criteria_scores.items() if v}
    return {
        "suite": "DocNotesSearch",
        "total": total,
        "is_last_step_ok": is_last_step_ok,
        "scored_cases": scored_cases,
        "criteria_avg": criteria_avg,
    }


def eval_previsit_summary():
    PrevisitSummarizer = _load_agent_graph_class("previsit_summary_agent", "PrevisitSummarizer")
    total = 0
    is_last_step_ok = 0
    scored_cases = 0
    criteria_scores: dict[str, list[float]] = {}
    criteria = {
        "completeness": "Score 0 to 5 for completeness: covers summary, meds, allergies, symptoms, concerns (or clearly marks unknown).",
        "structure_clarity": "Score 0 to 5 for clear organization, concise phrasing, and usefulness to a clinician.",
        "no_hallucination": "Score 0 to 5 for avoiding fabricated meds/allergies/history; should not invent specifics without evidence.",
    }
    suite_ctx = (
        root_span.new("PrevisitSummary") if root_span is not None else contextlib.nullcontext(None)
    )
    with (
        (_resources_dir() / "previsit_summary.jsonl").open() as fp,
        suite_ctx as suite_span,
    ):
        for i, line in enumerate(fp):
            row = json.loads(line)
            reference = row.get("reference", "")
            _input = row.get("input", {})
            patient_id = _input.get("patient_id")

            eval_ctx = (
                suite_span.new(f"Eval_{i}", test_input=line)
                if suite_span is not None
                else contextlib.nullcontext(None)
            )

            with eval_ctx as eval_span:
                graph = (
                    PrevisitSummarizer(catalog=catalog, span=eval_span)
                    if eval_span is not None
                    else PrevisitSummarizer(catalog=catalog)
                )
                state = PrevisitSummarizer.build_starting_state(patient_id=patient_id)
                user_message = json.dumps({"patient_id": patient_id})
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                result = graph.invoke(input=state)
                total += 1
                last_step = bool(result.get("is_last_step"))
                if last_step:
                    is_last_step_ok += 1
                if eval_span is not None:
                    eval_span["correctly_set_is_last_step"] = last_step

                summary = str(result.get("clinical_summary") or "")
                scores = _score_criteria(criteria, user_message, summary, reference)
                if scores:
                    scored_cases += 1
                    for k, v in scores.items():
                        criteria_scores.setdefault(k, []).append(v)
                    if eval_span is not None:
                        eval_span["quality"] = {"scores": scores, "reference": reference}

    criteria_avg = {k: (sum(v) / len(v)) for k, v in criteria_scores.items() if v}
    return {
        "suite": "PrevisitSummary",
        "total": total,
        "is_last_step_ok": is_last_step_ok,
        "scored_cases": scored_cases,
        "criteria_avg": criteria_avg,
    }


def eval_wearable_analytics():
    WearableAnalyzer = _load_agent_graph_class("wearable_analytics_agent", "WearableAnalyzer")
    total = 0
    is_last_step_ok = 0
    scored_cases = 0
    criteria_scores: dict[str, list[float]] = {}
    criteria = {
        "clinical_usefulness": "Score 0 to 5 for clinical usefulness: highlights key trends/alerts and provides appropriate interpretation.",
        "actionability": "Score 0 to 5 for actionable, practical next steps; prioritize urgency appropriately.",
        "no_fabrication": "Score 0 to 5 for avoiding fabricated vitals/diagnoses and appropriately stating uncertainty when data is missing.",
    }
    suite_ctx = (
        root_span.new("WearableAnalytics")
        if root_span is not None
        else contextlib.nullcontext(None)
    )
    with (
        (_resources_dir() / "wearable_analytics.jsonl").open() as fp,
        suite_ctx as suite_span,
    ):
        for i, line in enumerate(fp):
            row = json.loads(line)
            reference = row.get("reference", "")
            _input = row.get("input", {})
            patient_id = _input.get("patient_id")
            question = _input.get("question")

            eval_ctx = (
                suite_span.new(f"Eval_{i}", test_input=line)
                if suite_span is not None
                else contextlib.nullcontext(None)
            )

            with eval_ctx as eval_span:
                graph = (
                    WearableAnalyzer(catalog=catalog, span=eval_span)
                    if eval_span is not None
                    else WearableAnalyzer(catalog=catalog)
                )
                state = WearableAnalyzer.build_starting_state(
                    patient_id=patient_id,
                    question=question,
                )
                user_message = json.dumps({"patient_id": patient_id, "question": question})
                state["messages"].append(langchain_core.messages.HumanMessage(content=user_message))

                result = graph.invoke(input=state)
                total += 1
                last_step = bool(result.get("is_last_step"))
                if last_step:
                    is_last_step_ok += 1
                if eval_span is not None:
                    eval_span["correctly_set_is_last_step"] = last_step

                answer = str(result.get("answer") or "")
                scores = _score_criteria(criteria, user_message, answer, reference)
                if scores:
                    scored_cases += 1
                    for k, v in scores.items():
                        criteria_scores.setdefault(k, []).append(v)
                    if eval_span is not None:
                        eval_span["quality"] = {"scores": scores, "reference": reference}

    criteria_avg = {k: (sum(v) / len(v)) for k, v in criteria_scores.items() if v}
    return {
        "suite": "WearableAnalytics",
        "total": total,
        "is_last_step_ok": is_last_step_ok,
        "scored_cases": scored_cases,
        "criteria_avg": criteria_avg,
    }


if __name__ == "__main__":
    results = [
        eval_pulmonary_research(),
        eval_docnotes_search(),
        eval_previsit_summary(),
        eval_wearable_analytics(),
    ]

    for r in results:
        suite = str(r["suite"])
        total = int(r["total"])
        ok = int(r["is_last_step_ok"])
        scored_cases = int(r.get("scored_cases") or 0)
        print(f"{suite}: cases={total} scored={scored_cases} is_last_step={ok}/{total}")
        criteria_avg = r.get("criteria_avg") or {}
        for k in sorted(criteria_avg.keys()):
            v = criteria_avg[k]
            try:
                v = float(v)
            except Exception:
                continue
            print(f"  {k}={v:.3f}")
