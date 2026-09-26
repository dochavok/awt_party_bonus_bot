"""Engine speed (NF-1, NF-2): calculating a 20-character party takes under 200 ms."""

import time

import pytest

from tests.engine.scenarios import PlayerSpec, catalog_data, run, scenario_catalog

pytestmark = pytest.mark.milestone("M2")

# Everything except the one-holder entries, for every character.
_ENTRIES = tuple(
    name for name, spec in catalog_data()["entries"].items() if not spec.get("unique", False)
)


@pytest.mark.req("NF-1", "NF-2")
def test_a_20_character_party_is_calculated_in_under_200_ms() -> None:
    party = [
        PlayerSpec(
            name=f"Hero {n:02}",
            has=_ENTRIES,
            guilds=("GoTH", "Thieves", "Pirates", "Cult", "Rangers"),
            roles=("Guild Legend",),
            level=5 + n,
        )
        for n in range(20)
    ]
    catalog = scenario_catalog()
    run(party, catalog)  # warm up

    timings = []
    for _ in range(5):
        start = time.perf_counter()
        report, _ = run(party, catalog)
        timings.append(time.perf_counter() - start)

    assert len(report.recipients) == 20
    assert sorted(timings)[len(timings) // 2] < 0.200, f"median {sorted(timings)[2]:.3f} s"
