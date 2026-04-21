from pathlib import Path

import pytest

from app.services.ares_eval_loop_service import AresEvalLoopService, AresEvalSample


def _storage_path(tmp_path: Path) -> Path:
    return tmp_path / "runtime" / "ares-eval-loop.json"


def test_eval_loop_measures_all_required_quality_and_risk_metrics(tmp_path: Path) -> None:
    service = AresEvalLoopService(_storage_path(tmp_path))

    result = service.evaluate_and_record(
        run_id="run-1",
        sample=AresEvalSample(
            leads_reviewed=10,
            qualified_leads=7,
            responses_sent=8,
            quality_responses=6,
            conversion_opportunities=5,
            successful_conversions=2,
            false_positives=2,
            duplicate_work_items=1,
            operator_corrections=3,
        ),
    )

    assert result.run_id == "run-1"
    assert result.metrics.lead_quality == 0.7
    assert result.metrics.response_quality == 0.75
    assert result.metrics.conversion_quality == 0.4
    assert result.metrics.false_positive_rate == 0.2
    assert result.metrics.duplicate_work_rate == 0.1
    assert result.metrics.operator_correction_rate == 0.3


def test_eval_results_are_durable_and_inspectable(tmp_path: Path) -> None:
    storage_path = _storage_path(tmp_path)
    writer = AresEvalLoopService(storage_path)

    writer.evaluate_and_record(
        run_id="run-2",
        sample=AresEvalSample(
            leads_reviewed=4,
            qualified_leads=3,
            responses_sent=4,
            quality_responses=3,
            conversion_opportunities=2,
            successful_conversions=1,
            false_positives=1,
            duplicate_work_items=0,
            operator_corrections=1,
        ),
    )
    writer.save()

    reader = AresEvalLoopService(storage_path)
    entries = reader.load().entries

    assert storage_path.exists()
    assert len(entries) == 1
    assert entries[0].run_id == "run-2"
    assert entries[0].metrics.response_quality == 0.75


def test_metrics_contract_is_stable(tmp_path: Path) -> None:
    service = AresEvalLoopService(_storage_path(tmp_path))

    result = service.evaluate_and_record(
        run_id="run-contract",
        sample=AresEvalSample(
            leads_reviewed=0,
            qualified_leads=0,
            responses_sent=0,
            quality_responses=0,
            conversion_opportunities=0,
            successful_conversions=0,
            false_positives=0,
            duplicate_work_items=0,
            operator_corrections=0,
        ),
    )

    assert list(result.metrics.model_dump().keys()) == [
        "lead_quality",
        "response_quality",
        "conversion_quality",
        "false_positive_rate",
        "duplicate_work_rate",
        "operator_correction_rate",
    ]
    assert result.metrics.model_dump() == {
        "lead_quality": 0.0,
        "response_quality": 0.0,
        "conversion_quality": 0.0,
        "false_positive_rate": 0.0,
        "duplicate_work_rate": 0.0,
        "operator_correction_rate": 0.0,
    }


def test_eval_loop_rejects_impossible_metric_inputs_above_one(tmp_path: Path) -> None:
    service = AresEvalLoopService(_storage_path(tmp_path))

    with pytest.raises(ValueError, match="cannot exceed"):
        service.evaluate_and_record(
            run_id="run-impossible",
            sample=AresEvalSample(
                leads_reviewed=1,
                qualified_leads=2,
                responses_sent=1,
                quality_responses=1,
                conversion_opportunities=1,
                successful_conversions=1,
                false_positives=0,
                duplicate_work_items=0,
                operator_corrections=0,
            ),
        )


def test_concurrent_eval_writers_merge_history_instead_of_clobbering(tmp_path: Path) -> None:
    storage_path = _storage_path(tmp_path)
    writer_a = AresEvalLoopService(storage_path)
    writer_b = AresEvalLoopService(storage_path)

    writer_a.load()
    writer_b.load()

    writer_a.evaluate_and_record(
        run_id="run-a",
        sample=AresEvalSample(
            leads_reviewed=2,
            qualified_leads=1,
            responses_sent=2,
            quality_responses=1,
            conversion_opportunities=1,
            successful_conversions=0,
            false_positives=0,
            duplicate_work_items=0,
            operator_corrections=0,
        ),
    )
    writer_a.save()

    writer_b.evaluate_and_record(
        run_id="run-b",
        sample=AresEvalSample(
            leads_reviewed=3,
            qualified_leads=2,
            responses_sent=3,
            quality_responses=2,
            conversion_opportunities=1,
            successful_conversions=1,
            false_positives=0,
            duplicate_work_items=0,
            operator_corrections=0,
        ),
    )
    writer_b.save()

    entries = AresEvalLoopService(storage_path).load().entries

    assert [entry.run_id for entry in entries] == ["run-a", "run-b"]


def test_eval_loop_load_raises_predictable_error_for_corrupt_json(tmp_path: Path) -> None:
    storage_path = _storage_path(tmp_path)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{ definitely-not-valid-json", encoding="utf-8")

    service = AresEvalLoopService(storage_path)

    with pytest.raises(ValueError, match="Corrupted Ares eval loop state"):
        service.load()
