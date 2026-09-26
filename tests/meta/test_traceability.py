"""Traceability (TF-3) and milestone (TF-4) bookkeeping, checked against the documents (M1)."""

import pytest

from tests.conftest import finished_milestones
from tests.support.traceability import milestones, requirements

pytestmark = pytest.mark.milestone("M1")


@pytest.mark.req("TF-3")
def test_requirement_ids_are_read_from_the_document() -> None:
    reqs = requirements()
    for req_id in [
        "CH-1",
        "CT-9",
        "HV-6",
        "SG-5",
        "SE-6",
        "OUT-2a",
        "OUT-3b",
        "AD-2",
        "NF-1",
        "NF-12",
        "DB-7",
        "DP-4",
        "TF-2a",
        "TF-6",
        "TS-18",
        "BG-3",
    ]:
        assert req_id in reqs
    assert reqs["CH-6"].priority == "S"
    assert reqs["OUT-8"].priority == "C"
    assert reqs["HV-4"].priority == "M"
    assert reqs["NF-4"].priority == "M"  # the NF table has no priority column


@pytest.mark.req("TF-3")
def test_section_4_rules_and_sample_game_are_requirements() -> None:
    reqs = requirements()
    assert {f"4.{n}" for n in range(1, 14)} <= set(reqs)
    assert "4.14" not in reqs
    assert "9.1" in reqs


@pytest.mark.req("TF-4")
def test_milestones_are_read_from_section_17() -> None:
    assert milestones() == ("M1", "M2", "M3", "M4", "M5", "M6")


@pytest.mark.req("TF-4")
def test_finished_milestones_are_known() -> None:
    assert finished_milestones() <= set(milestones())
