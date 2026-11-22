"""The real catalog in catalog/ (TS-4, CT-7): it loads and passes every check, and
Excalibur, a modifier item, counts as rule 4.6 says.

The catalog files are written in M2; until then this runs as an expected failure.
The check that no previously released entry disappears runs in CI against the
previous commit (see .github/workflows/ci.yml), since only git knows that version.
"""

from functools import cache

import pytest

from awt_bonus.catalog import Catalog, EntryKind, Membership, load_catalog
from awt_bonus.ids import EntryId
from tests.engine.scenarios import PlayerSpec, run
from tests.support.traceability import ROOT

pytestmark = pytest.mark.milestone("M2")


@pytest.mark.req("TS-4", "CT-7", "CT-1")
def test_the_real_catalog_loads_and_passes_every_check() -> None:
    load_catalog(ROOT / "catalog")


@pytest.mark.milestone("M9")
@pytest.mark.req("OUT-10", "CT-5")
def test_the_real_catalog_has_the_knights_of_crail_guild() -> None:
    catalog = load_catalog(ROOT / "catalog")
    guild = catalog.guild_named("Knights of Crail")
    assert guild is not None
    assert guild.short_name == "KoC"
    assert guild.membership is Membership.OPEN
    assert not guild.secret
    assert catalog.guild_named("KoC") == guild
    assert not catalog.guild_entries(guild.id), "its items have no always-on bonuses"


@cache
def _real_catalog() -> Catalog:
    return load_catalog(ROOT / "catalog")


def _ally_totals(holder: tuple[str, ...], other: tuple[str, ...] = ()) -> dict[str, int]:
    """An ally's non-zero totals from a holder (and maybe a second giver)."""
    players = [PlayerSpec("Thomas", has=holder), PlayerSpec("Ally")]
    if other:
        players.append(PlayerSpec("Other", has=other))
    report, _ = run(players, _real_catalog())
    return {stat: n for stat, n in report.recipient("Ally").totals.items() if n}


AURAS = ("holy_aura", "bolstering_aura")


@pytest.mark.req("4.6", "TS-4")
@pytest.mark.parametrize(
    ("holder", "expected"),
    [
        (("excalibur",), {}),
        ((*AURAS, "excalibur"), {"CM": 3, "CR vs fear": 3}),
        ((*AURAS, "devotion_3", "excalibur"), {"CM": 4, "CR vs fear": 4}),
    ],
    ids=["nothing by itself", "+1 to each aura", "adds to Devotion III"],
)
def test_excalibur_adds_1_to_each_of_its_holders_auras(
    holder: tuple[str, ...], expected: dict[str, int]
) -> None:
    assert _ally_totals(holder) == expected


@pytest.mark.req("4.6", "TS-4")
def test_excalibur_raises_only_its_holders_auras() -> None:
    ally = _ally_totals(("excalibur", "wills_ward_stone"), other=("bolstering_aura",))
    assert ally == {"CM": 7}, "Ward Stone's 5 isn't an aura, and Other's aura stays 2"


@pytest.mark.req("HV-6", "TS-4")
def test_excalibur_is_a_unique_item() -> None:
    entry = _real_catalog().entries[EntryId("excalibur")]
    assert entry.name == "Excalibur"
    assert entry.kind is EntryKind.ITEM
    assert entry.unique
