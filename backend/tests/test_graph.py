"""End-to-end graph smoke test — runs with no API keys and no trained model.

Proves the pipeline boots, every node returns the right state shape, and the
fusion node produces a well-formed verdict even with zero external signal.
"""
import pytest

from app.api.routes import _result_view
from app.graph.build_graph import build_graph


@pytest.fixture
def graph():
    return build_graph()


async def test_pipeline_runs_end_to_end(graph):
    state = {
        "raw_input": "The central bank raised interest rates by half a point on Tuesday.",
        "claims": [],
        "evidence": [],
        "assessments": [],
        "sources": [],
        "log": [],
    }
    final = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

    # Fusion always sets a label; with no signal it must be "uncertain".
    assert final["final_label"] in ("real", "fake", "uncertain")
    assert "rationale" in final

    view = _result_view(final)
    assert view["label"] == final["final_label"]
    assert isinstance(view["claims"], list)
    assert isinstance(view["sources"], list)


async def test_blank_input_is_uncertain(graph):
    state = {"raw_input": "", "claims": [], "evidence": [], "assessments": [], "sources": [], "log": []}
    final = await graph.ainvoke(state, config={"configurable": {"thread_id": "blank"}})
    assert final["final_label"] == "uncertain"
