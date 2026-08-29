from datetime import UTC

from x2video.domain.models import (
    Artifact,
    ContentGoal,
    EvidencePack,
    RunState,
    Storyboard,
)


def test_versioned_contracts_are_timezone_aware() -> None:
    goal = ContentGoal(run_id="run_1", query="今日 AI 新闻")
    assert goal.schema_version == "1.0"
    assert goal.created_at.tzinfo == UTC
    assert goal.budget.max_repairs == 2


def test_artifact_has_required_provenance() -> None:
    artifact = Artifact(
        run_id="run_1",
        input_hash="abc",
        kind="publish_kit",
        path="final/demo",
    )
    dumped = artifact.model_dump(mode="json")
    for key in ("schema_version", "run_id", "created_at", "producer_version", "input_hash"):
        assert dumped[key]


def test_nested_contracts_validate() -> None:
    pack = EvidencePack(run_id="run_1", candidate_id="candidate_1")
    board = Storyboard(run_id="run_1", template="news_recap")
    assert pack.risk_flags == []
    assert board.scenes == []
    assert RunState.RESEARCH.value == "RESEARCH"
