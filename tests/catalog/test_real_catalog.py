"""The real catalog in catalog/ (TS-4, CT-7): it loads and passes every check.

The catalog files are written in M2; until then this runs as an expected failure.
The check that no previously released entry disappears runs in CI against the
previous commit (see .github/workflows/ci.yml), since only git knows that version.
"""

import pytest

from awt_bonus.catalog import Membership, load_catalog
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
