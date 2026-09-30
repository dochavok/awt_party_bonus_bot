"""Item classes in the catalog (CT-10, CT-4, CT-6, CT-7, section 8.5).

Builds small catalogs in memory from the engine scenario catalog, with the item
classes and class items from tests/engine/test_item_classes.py, each changed or
broken in one known way.
"""

from typing import Any

import pytest

from awt_bonus.catalog import CatalogError, check_no_removed, load_catalog, parse_catalog
from tests.engine.test_item_classes import class_catalog_data
from tests.support.traceability import ROOT

pytestmark = pytest.mark.milestone("M8")


def _problems(data: dict[str, Any]) -> str:
    with pytest.raises(CatalogError) as caught:
        parse_catalog(data)
    assert caught.value.problems, "a CatalogError must list its problems"
    return "\n".join(caught.value.problems)


@pytest.mark.req("CT-10", "CT-4")
def test_item_classes_and_the_two_class_fields_load() -> None:
    parse_catalog(class_catalog_data())


@pytest.mark.req("CT-10", "CT-7")
def test_an_entry_naming_an_unknown_class_is_refused() -> None:
    data = class_catalog_data()
    data["entries"]["Will Passion's Pendant"] = {
        **data["entries"]["Will Passion's Pendant"],
        "needs_item_class": "sausage",
    }
    data["entries"]["Will Passions Adventure Token"] = {
        **data["entries"]["Will Passions Adventure Token"],
        "per_item_class": "mustard",
    }
    problems = _problems(data)
    assert "sausage" in problems
    assert "mustard" in problems, "every unknown class is reported"


@pytest.mark.req("CT-10", "CT-7")
def test_class_names_and_other_names_must_be_unique_ignoring_case() -> None:
    data = class_catalog_data()
    data["item_classes"] = {
        **data["item_classes"],
        "sausages": {"other_names": ["HOTDOG"], "description": "Sausage themed items"},
    }
    assert "hotdog" in _problems(data).casefold()


@pytest.mark.req("CT-10", "CT-7", "CT-6")
def test_a_class_that_disappears_is_reported_and_a_retired_one_is_not() -> None:
    previous = class_catalog_data()
    previous["item_classes"] = {
        **previous["item_classes"],
        "cold": {"description": "Items against extreme cold"},
    }
    current = class_catalog_data()
    current["item_classes"] = {
        **current["item_classes"],
        "cold": {"description": "Items against extreme cold", "retired": True},
    }
    del current["item_classes"]["glizzy"]
    del current["entries"]["Glizzy from God"]
    current["entries"]["Glizzy from God"] = {"kind": "item", "retired": True}

    problems = "\n".join(check_no_removed(parse_catalog(previous), parse_catalog(current)))
    assert "glizzy" in problems
    assert "cold" not in problems, "retiring a class is allowed (CT-6)"


@pytest.mark.req("CT-10", "TS-4")
def test_the_real_catalog_has_the_passion_and_glizzy_classes() -> None:
    catalog = load_catalog(ROOT / "catalog")
    names = {
        item_class.name: {n.casefold() for n in item_class.other_names}
        for item_class in catalog.item_classes.values()
    }
    assert "will passion" in names["passion"]
    assert "hotdog" in names["glizzy"]
