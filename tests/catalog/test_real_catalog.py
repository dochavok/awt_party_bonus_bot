"""The real catalog in catalog/ (TS-4, CT-7): it loads and passes every check, and
entries whose catalog data needs checking against the engine count as section 8 says
(e.g. Excalibur, a modifier item).

The catalog files are written in M2; until then this runs as an expected failure.
The check that no previously released entry disappears runs in CI against the
previous commit (see .github/workflows/ci.yml), since only git knows that version.
"""

import pytest

from awt_bonus.catalog import EntryKind, Membership, load_catalog
from awt_bonus.ids import EntryId, StatId
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


def _ally_totals(*holder: str, other: tuple[str, ...] = ()) -> dict[str, int]:
    """What an ally with nothing receives from a holder (and maybe a second giver)."""
    players = [PlayerSpec("Thomas", has=holder), PlayerSpec("Ally")]
    if other:
        players.append(PlayerSpec("Other", has=other))
    report, _ = run(players, load_catalog(ROOT / "catalog"))
    totals = report.recipient("Ally").totals
    return {stat: totals.get(StatId(stat), 0) for stat in ("CM", "CR vs fear")}


@pytest.mark.req("4.6", "TS-4")
def test_excalibur_adds_1_to_each_of_its_holders_auras() -> None:
    assert _ally_totals("holy_aura", "bolstering_aura") == {"CM": 2, "CR vs fear": 2}
    assert _ally_totals("holy_aura", "bolstering_aura", "excalibur") == {
        "CM": 3,
        "CR vs fear": 3,
    }


@pytest.mark.req("4.6", "TS-4")
def test_excalibur_adds_to_devotion_iii() -> None:
    held = ("holy_aura", "bolstering_aura", "devotion_3", "excalibur")
    assert _ally_totals(*held) == {"CM": 4, "CR vs fear": 4}


@pytest.mark.req("4.6", "TS-4")
def test_excalibur_raises_only_its_holders_auras() -> None:
    ally = _ally_totals("excalibur", "wills_ward_stone", other=("bolstering_aura",))
    assert ally == {"CM": 7, "CR vs fear": 0}, "Ward Stone 5 isn't an aura; Other's aura stays 2"


@pytest.mark.req("4.6", "TS-4")
def test_excalibur_gives_nothing_by_itself() -> None:
    assert _ally_totals("excalibur") == {"CM": 0, "CR vs fear": 0}, "its +20 CM is the holder's"


@pytest.mark.req("HV-6", "TS-4")
def test_excalibur_is_a_unique_item() -> None:
    entry = load_catalog(ROOT / "catalog").entries[EntryId("excalibur")]
    assert entry.name == "Excalibur"
    assert entry.kind is EntryKind.ITEM
    assert entry.unique
