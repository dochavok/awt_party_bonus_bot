"""Catalog loading and validation (CT-2, CT-4, CT-5, CT-6, CT-7, TS-4).

Uses the small catalogs in tests/fixtures/catalogs/, each valid or broken in one
known way, plus the two test catalogs the other tests rely on.
"""

import shutil
from pathlib import Path

import pytest

from awt_bonus.catalog import CatalogError, check_no_removed, load_catalog, load_catalog_file
from awt_bonus.catalog.__main__ import main
from tests.engine.scenarios import scenario_catalog
from tests.support.world import FIXTURES

pytestmark = pytest.mark.milestone("M2")

CATALOGS = FIXTURES / "catalogs"


def _problems(path: Path) -> str:
    with pytest.raises(CatalogError) as caught:
        load_catalog_file(path)
    assert caught.value.problems, "a CatalogError must list its problems"
    return "\n".join(caught.value.problems)


@pytest.mark.req("CT-7", "CT-4", "CT-5")
def test_a_valid_catalog_loads() -> None:
    load_catalog_file(CATALOGS / "valid.yaml")


@pytest.mark.req("TS-1", "CT-4", "CT-5")
def test_the_engine_scenario_catalog_loads() -> None:
    scenario_catalog()


@pytest.mark.req("TF-2a", "CT-2", "CT-4", "CT-5")
def test_the_command_test_catalog_loads() -> None:
    load_catalog_file(FIXTURES / "catalog.yaml")


@pytest.mark.req("CT-7", "CT-2")
def test_duplicate_ids_are_refused() -> None:
    assert "shield_song" in _problems(CATALOGS / "invalid-duplicate-id.yaml")


@pytest.mark.req("CT-7")
def test_duplicate_names_are_refused() -> None:
    assert "Shield Song" in _problems(CATALOGS / "invalid-duplicate-name.yaml")


@pytest.mark.req("CT-7")
def test_an_unknown_stat_is_refused() -> None:
    assert "XP" in _problems(CATALOGS / "invalid-unknown-stat.yaml")


@pytest.mark.req("CT-7")
def test_every_unknown_reference_is_reported() -> None:
    problems = _problems(CATALOGS / "invalid-unknown-reference.yaml")
    assert "lost_song" in problems  # replaces an entry that doesn't exist
    assert "night_watch" in problems  # belongs to a guild that doesn't exist
    assert "CR2" in problems  # a parent stat that doesn't exist


@pytest.mark.req("CT-7", "CT-4")
def test_a_badly_formatted_catalog_is_refused() -> None:
    problems = _problems(CATALOGS / "invalid-format.yaml")
    assert "fireball" in problems  # kind "spell" isn't a kind
    assert "shield_song" in problems  # the amount isn't a number


@pytest.mark.req("CT-7")
def test_a_catalog_split_across_files_loads() -> None:
    load_catalog(CATALOGS / "split-valid")


@pytest.mark.req("CT-7")
def test_ids_must_be_unique_across_files() -> None:
    with pytest.raises(CatalogError) as caught:
        load_catalog(CATALOGS / "split-duplicate")
    assert "shield_song" in "\n".join(caught.value.problems)


@pytest.mark.req("CT-7", "CT-6")
def test_an_entry_that_disappears_is_reported() -> None:
    previous = load_catalog_file(CATALOGS / "previous.yaml")
    current = load_catalog_file(CATALOGS / "valid.yaml")
    problems = "\n".join(check_no_removed(previous, current))
    assert "war_drum" in problems
    assert "old_lamp" not in problems, "retiring an entry is allowed (CT-6)"


@pytest.mark.req("CT-7")
def test_an_unchanged_or_extended_catalog_has_nothing_removed() -> None:
    previous = load_catalog_file(CATALOGS / "previous.yaml")
    current = load_catalog_file(CATALOGS / "valid.yaml")
    assert check_no_removed(current, current) == []
    assert check_no_removed(current, previous) == []  # adding War Drum is fine


@pytest.mark.req("CT-7")
def test_the_ci_check_passes_a_valid_catalog(tmp_path: Path) -> None:
    previous = tmp_path / "previous"
    shutil.copytree(CATALOGS / "split-valid", previous)
    assert main(["check", str(CATALOGS / "split-valid")]) == 0
    assert main(["check", str(CATALOGS / "split-valid"), "--previous", str(previous)]) == 0


@pytest.mark.req("CT-7")
def test_the_ci_check_fails_an_invalid_catalog() -> None:
    assert main(["check", str(CATALOGS / "split-duplicate")]) != 0


@pytest.mark.req("CT-7")
def test_the_ci_check_fails_when_an_entry_disappears(tmp_path: Path) -> None:
    previous = tmp_path / "previous"
    shutil.copytree(CATALOGS / "split-valid", previous)
    (previous / "extra.yaml").write_text(
        "entries:\n  war_drum: {name: War Drum, kind: item, gives: {CM: 1}}\n", encoding="utf-8"
    )
    assert main(["check", str(CATALOGS / "split-valid"), "--previous", str(previous)]) != 0
