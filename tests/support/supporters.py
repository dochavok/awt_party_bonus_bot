"""The command-level test catalog with supporting sit-outs allowed (SE-7, CT-5).

The fixture catalog (``tests/fixtures/catalog.yaml``) doesn't allow Support while
sitting out, so these tests change a copy of it instead of the fixture (TF-6),
as other command tests do for catalog changes.
"""

from awt_bonus.catalog import Catalog, parse_catalog
from tests.support.world import catalog_data

ALLOWED_ROLES = ("Guild Champion", "Guild Legend")
"""The roles allowed to give Support while sitting out, as in the real catalog."""

JOIN_TEXT = "Guild tiers come from the test Patreon."
"""The test guild's how-to-join text, which the SE-7 refusal shows."""


def supporter_catalog() -> Catalog:
    data = catalog_data()
    guild = data["guilds"]["the_guild"]
    guild["from_roles"][0]["while_sitting_out"] = list(ALLOWED_ROLES)
    guild["how_to_join"] = JOIN_TEXT
    return parse_catalog(data)
