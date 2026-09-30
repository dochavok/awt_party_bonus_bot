"""Output commands (requirements 6.6: OUT-1 to OUT-7, and OUT-9 /help), message size
(TS-7), totals only (rule 4.13), review (AD-2) and the section 9 numbers through the
commands.

Numbers are checked on the reply's report; text only for what must, or must never,
appear (TF-1). Most tests use the sample game: Isla plays Ioseph, Kit plays Kael,
Cora plays Crateris (and owns Elowen), Cole plays Chris, Maya plays Mira; Dana has
no character; DM Sam and Bob sit out; Vic (Vex) isn't in voice. The /help tests
(OUT-9, M6) use the setup fixture instead: its players are at different stages of
setting up.
"""

import re
from collections.abc import Mapping

import pytest

from awt_bonus.commands import OptionValue
from awt_bonus.engine import Reason
from awt_bonus.ids import StatId
from tests.support.text import PRONOUNS, counted, lines_with, mentions, recipient, stat
from tests.support.world import MakeWorld

M3 = pytest.mark.milestone("M3")
M4 = pytest.mark.milestone("M4")
M6 = pytest.mark.milestone("M6")
M7 = pytest.mark.milestone("M7")


def _stats(
    cm: int, cr: int, fear: int, stealth: int, escape: int, damage: int = 0
) -> dict[str, int]:
    return {
        "CM": cm, "CR": cr, "CR vs fear": fear, "CR stealth": stealth, "CR escape": escape,
        "CR would hurt": cr, "Damage": damage, "Damage reduction": 0, "Healing": 0,
    }  # fmt: skip


SAMPLE_TOTALS = {
    "Ioseph": _stats(10, 5, 8, 5, 5),
    "Kael": _stats(18, 10, 13, 10, 10, damage=1),
    "Crateris": _stats(12, 10, 10, 10, 10),
    "Chris": _stats(23, 10, 13, 12, 11),
    "Mira": _stats(33, 10, 13, 12, 11),
    "Dana": _stats(20, 10, 13, 10, 10),
}
"""Section 9.1's /partybonus table and combat notes."""

SAMPLE_DMS = pytest.mark.dm("Q1", "Q2", "Q3", "Q6")


def _all_totals(reply_totals: Mapping[StatId, int]) -> dict[str, int]:
    return {stat: reply_totals.get(StatId(stat), 0) for stat in SAMPLE_TOTALS["Ioseph"]}


# ---------------------------------------------------------------- OUT-1: /partybonus


@M4
@pytest.mark.req("OUT-1", "OUT-5", "9.1", "SG-4")
@SAMPLE_DMS
async def test_partybonus_is_public_with_every_counted_characters_totals(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus")

    assert not reply.private
    assert counted(reply) == set(SAMPLE_TOTALS)
    for name, expected in SAMPLE_TOTALS.items():
        assert _all_totals(recipient(reply, name).totals) == expected, name
    for name in SAMPLE_TOTALS:
        assert name in reply.text
    for value in ["+10", "+18", "+12", "+23", "+33", "+20"]:
        assert value in reply.text


@M4
@pytest.mark.req("OUT-1", "OUT-5")
async def test_partybonus_private_true_is_a_private_check(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus", private=True)
    assert reply.private
    assert counted(reply) == set(SAMPLE_TOTALS)


@M4
@pytest.mark.req("OUT-1", "4.7")
async def test_partybonus_shows_only_cr_subtypes_that_differ_from_cr(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus")

    for shown in ["CR vs fear", "CR stealth", "CR escape"]:
        assert shown in reply.text
    assert "would hurt" not in reply.text  # equals CR for everyone


@M4
@pytest.mark.req("OUT-1", "4.13")
async def test_partybonus_shows_combat_notes_effects_and_totals_only(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus")

    assert lines_with(reply.text, "Kael", "Damage")
    assert "extra hearts dealt when attacking" in reply.text  # the note's description
    assert "Resistance to damage from an Evil source" in reply.text
    for contribution in [
        "Seraph's Affection", "Champion of Power", "Bolstering Aura", "Wills ward stone",
        "Inspiring Presence", "Support",
    ]:  # fmt: skip
        assert contribution not in reply.text, f"totals only: {contribution}"


@M4
@pytest.mark.req("OUT-1", "SE-5")
async def test_partybonus_lists_members_with_no_character(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus")
    assert lines_with(reply.text, "Dana")
    assert "/character register" in reply.text


@M4
@pytest.mark.req("OUT-1", "OUT-2", "4.12")
@pytest.mark.parametrize(("command", "options"), [("partybonus", {}), ("mybonus", {})])
async def test_conditional_bonuses_are_shown_with_their_condition_not_in_totals(
    make_world: MakeWorld, command: str, options: dict[str, OptionValue]
) -> None:
    world = await make_world("sample-game")
    world.discord.move(world.user("vic"), world.channel("AWT Voice"))  # Vex: Commanding Presence
    reply = await world.run("isla", command, **options)

    assert "Commanding Presence" in reply.text
    assert "same range" in reply.text
    # Vex's Aura of Hope (+10 CM) counts; Commanding Presence's +5 doesn't.
    assert stat(reply, "Ioseph", "CM") == 20


# ---------------------------------------------------------------- OUT-2: /mybonus


@M4
@pytest.mark.req("OUT-2", "OUT-5", "9.1", "4.13")
@SAMPLE_DMS
async def test_mybonus_shows_one_characters_totals_privately(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("maya", "mybonus", character="Mira")

    assert reply.private
    assert _all_totals(recipient(reply, "Mira").totals) == SAMPLE_TOTALS["Mira"]
    for value in ["+33", "+10", "+13", "+12", "+11"]:
        assert value in reply.text
    assert "Resistance to damage from an Evil source" in reply.text
    for contribution in ["Seraph's Affection", "Champion of Power", "Wills ward stone"]:
        assert contribution not in reply.text, f"totals only: {contribution}"


@M4
@pytest.mark.req("OUT-2")
async def test_mybonus_shows_combat_notes(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("kit", "mybonus")
    assert "Damage" in reply.text


@M4
@pytest.mark.req("OUT-2", "CH-5")
async def test_mybonus_has_no_level_note_when_no_bonus_needs_the_level(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("cole", "mybonus")  # Chris: no level, but not in the Cult
    assert "Chris" in reply.text
    assert stat(reply, "Chris", "CM") == 23
    assert "/character level" not in reply.text


# ---------------------------------------------------------------- OUT-2a: not-current notice


@M4
@pytest.mark.req("OUT-2a", "9.1")
@SAMPLE_DMS
@pytest.mark.parametrize("command", ["mybonus", "breakdown"])
async def test_a_non_current_character_is_shown_in_the_current_ones_place(
    make_world: MakeWorld, command: str
) -> None:
    world = await make_world("sample-game")
    await world.set_current("cora", "Elowen")
    reply = await world.run("cora", command, character="Crateris")

    assert "Elowen" in reply.text  # the notice names the character being played
    assert "/play Crateris" in reply.text
    assert counted(reply) == set(SAMPLE_TOTALS)  # Crateris in Elowen's place
    for name, expected in SAMPLE_TOTALS.items():
        assert _all_totals(recipient(reply, name).totals) == expected, name


@M4
@pytest.mark.req("OUT-2a", "OUT-6")
@pytest.mark.parametrize("command", ["mybonus", "breakdown"])
async def test_the_notice_for_someone_elses_character_has_no_play_hint(
    make_world: MakeWorld, command: str
) -> None:
    world = await make_world("sample-game")
    await world.set_current("cora", "Elowen")
    reply = await world.run("isla", command, character="Crateris")

    assert "Elowen" in reply.text
    assert "/play" not in reply.text
    assert "Crateris" in counted(reply)
    assert "Elowen" not in counted(reply)


@M3
@pytest.mark.req("OUT-2a")
@pytest.mark.parametrize("command", ["mybonus", "breakdown"])
async def test_no_notice_for_the_current_character(make_world: MakeWorld, command: str) -> None:
    world = await make_world("sample-game")
    reply = await world.run("cora", command, character="Crateris")

    assert "Crateris" in reply.text
    assert "Crateris" in counted(reply)
    assert "Elowen" not in reply.text
    assert "/play" not in reply.text


# ---------------------------------------------------------------- OUT-3: party /breakdown


@M4
@pytest.mark.req("OUT-3", "OUT-5", "9.1")
@SAMPLE_DMS
async def test_party_breakdown_lists_every_bonus_in_play_and_its_contributors(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "breakdown")

    assert reply.private
    for bonus in [
        "Support", "Seraph's Affection", "Champion of Power", "Cult of the Dragon", "Holy Aura",
        "Bolstering Aura", "Wills ward stone", "Inspiring Presence", "Protective Aura",
    ]:  # fmt: skip
        assert bonus in reply.text, bonus
    for rank in ["Guild Vanguard", "Junior Adventurer", "High Priest"]:
        assert rank in reply.text, rank
    assert mentions(reply.text, "level 8")  # the Cult bonus depends on the recipient's level
    assert mentions(reply.text, "level 15")
    assert "Devotion III" in reply.text
    assert "Resistance to damage from an Evil source" in reply.text
    for total in ["+10", "+18", "+12", "+23", "+33", "+20"]:
        assert total in reply.text, total  # the working ends in each total
    assert "DM Sam" in reply.text
    assert "Bob" in reply.text
    for name, expected in SAMPLE_TOTALS.items():
        assert _all_totals(recipient(reply, name).totals) == expected, name


@M4
@pytest.mark.req("AD-2", "OUT-3")
async def test_anyone_can_review_the_party_breakdown_even_when_sitting_out(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("sam", "breakdown")

    assert reply.private
    assert counted(reply) == set(SAMPLE_TOTALS)
    for name in SAMPLE_TOTALS:
        assert name in reply.text


# ---------------------------------------------------------------- OUT-3a: /breakdown <character>


@M4
@pytest.mark.req("OUT-3a", "OUT-5", "9.1")
@SAMPLE_DMS
async def test_character_breakdown_shows_every_contribution_with_giver(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("cora", "breakdown", character="Crateris")

    assert reply.private
    assert _all_totals(recipient(reply, "Crateris").totals) == SAMPLE_TOTALS["Crateris"]
    assert lines_with(reply.text, "Support", "Ioseph")
    assert lines_with(reply.text, "Support", "Kael")
    assert lines_with(reply.text, "Seraph's Affection", "Ioseph")
    assert lines_with(reply.text, "Champion of Power", "Ioseph")
    assert "Inspiring Presence" in reply.text
    assert "Chris" in reply.text
    assert "Mira" in reply.text
    assert "+12" in reply.text
    assert "+10" in reply.text
    assert mentions(reply.text, "level 22")


@M4
@pytest.mark.req("OUT-3a", "4.6")
async def test_character_breakdown_shows_modifiers_and_what_the_character_gives(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("cora", "breakdown", character="Crateris")

    assert lines_with(reply.text, "Holy Aura", "Devotion III")
    assert lines_with(reply.text, "Bolstering Aura", "Devotion III")
    assert "Wills ward stone" in reply.text
    assert "Protective Aura" in reply.text
    assert "Cult of the Dragon" in reply.text or "High Priest" in reply.text


@M4
@pytest.mark.req("OUT-3a", "9.1")
async def test_character_breakdown_not_applied_lists_what_the_character_misses(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("cora", "breakdown", character="Crateris")

    assert reply.report is not None
    report = reply.report
    excluded = {
        report.give(n.give).entry
        for n in recipient(reply, "Crateris").not_applied
        if n.reason is Reason.GIVER_EXCLUDED
    }
    assert {"holy_aura", "bolstering_aura", "protective_aura", "wills_ward_stone"} <= excluded
    assert "high_priest" in excluded


@M4
@pytest.mark.req("OUT-3a", "CH-5")
async def test_character_breakdown_shows_combat_notes(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("kit", "breakdown", character="Kael")
    assert "Damage" in reply.text
    assert "Crateris" in reply.text  # the High Priest gives it


# ---------------------------------------------------------------- OUT-3b, TS-7: message size


@M4
@pytest.mark.req("OUT-3b", "TS-7", "NF-2")
@pytest.mark.parametrize(
    ("command", "options"),
    [
        ("partybonus", {}),
        ("breakdown", {}),
        ("breakdown", {"character": "Hero Aldric"}),
        ("mybonus", {}),
    ],
)
async def test_long_output_is_split_under_2000_characters_never_mid_line(
    make_world: MakeWorld, command: str, options: dict[str, OptionValue]
) -> None:
    world = await make_world("big-party")
    reply = await world.run("p01", command, **options)

    assert reply.messages
    for message in reply.messages:
        assert 0 < len(message) <= 2000
    heroes = [c.name for p in world.spec.players for c in p.characters]
    if command in {"partybonus", "breakdown"} and "character" not in options:
        for hero in heroes:
            assert hero in reply.text, f"{hero} was cut off"
    if command == "partybonus":
        for message in reply.messages:
            for line in message.splitlines():
                if any(hero in line for hero in heroes):
                    assert re.search(r"\+\d", line), f"a totals line was cut: {line!r}"


@M4
@pytest.mark.req("OUT-3b", "TS-7")
async def test_a_very_long_breakdown_needs_several_messages(make_world: MakeWorld) -> None:
    world = await make_world("big-party")
    reply = await world.run("p01", "breakdown")
    assert len(reply.messages) > 1


# ---------------------------------------------------------------- OUT-4: not in voice


@M3
@pytest.mark.req("OUT-4")
@pytest.mark.parametrize("command", ["mybonus", "breakdown"])
async def test_with_no_party_present_the_reply_shows_what_the_character_gives(
    make_world: MakeWorld, command: str
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("vic", command, character="Vex")

    assert reply.private
    assert "Aura of Hope" in reply.text
    assert "Commanding Presence" in reply.text


# ---------------------------------------------------------------- OUT-5: who sees replies


_PRIVATE_REPLIES: list[tuple[str, str, str, dict[str, OptionValue]]] = [
    ("M3", "craig", "mybonus", {}),
    ("M3", "craig", "mybonus", {"character": "Ioseph"}),
    ("M3", "craig", "breakdown", {}),
    ("M3", "craig", "breakdown", {"character": "Crateris"}),
    ("M3", "craig", "catalog", {}),
    ("M3", "craig", "catalog", {"entry": "Holy Aura"}),
    ("M3", "craig", "play", {"character": "Elowen"}),
    ("M3", "craig", "sitout", {}),
    ("M3", "craig", "sitin", {}),
    ("M3", "newbie", "character register", {"name": "Pip"}),
    ("M3", "craig", "character list", {}),
    ("M3", "craig", "character rename", {"character": "Elowen", "new": "Elowyn"}),
    ("M3", "craig", "character level", {"character": "Elowen", "level": 13}),
    ("M3", "craig", "add", {"character": "Elowen", "entry": "Holy Aura"}),
    ("M3", "craig", "remove", {"character": "Crateris", "entry": "Holy Aura"}),
    ("M4", "craig", "guild join", {"character": "Elowen", "guild": "Pirate Coalition"}),
    ("M4", "craig", "guild leave", {"character": "Crateris", "guild": "Cult of the Dragon"}),
    ("M5", "craig", "request", {"text": "Please add the Dragon Scale item"}),
]


@pytest.mark.req("OUT-5")
@pytest.mark.parametrize(
    ("handle", "command", "options"),
    [
        pytest.param(
            handle,
            command,
            options,
            marks=pytest.mark.milestone(milestone),
            id=f"{command}-{'-'.join(map(str, options.values())) or 'none'}",
        )
        for milestone, handle, command, options in _PRIVATE_REPLIES
    ],
)
async def test_every_reply_except_partybonus_is_private(
    make_world: MakeWorld, handle: str, command: str, options: dict[str, OptionValue]
) -> None:
    world = await make_world("setup")
    reply = await world.run(handle, command, **options)
    assert reply.private, f"/{command} must reply privately"


@M3
@pytest.mark.req("OUT-5")
async def test_partybonus_is_public_by_default(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    assert not (await world.run("craig", "partybonus")).private
    assert (await world.run("craig", "partybonus", private=True)).private


# ---------------------------------------------------------------- OUT-6: anyone's character


@M3
@pytest.mark.req("OUT-6")
@pytest.mark.parametrize("command", ["mybonus", "breakdown"])
async def test_a_player_can_look_up_anyones_character(make_world: MakeWorld, command: str) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", command, character="Bryn")

    assert "Bryn" in reply.text
    assert stat(reply, "Bryn", "CR vs fear") == 2


# ---------------------------------------------------------------- OUT-7: no pronouns


def _pronoun_views() -> list[tuple[str, str, dict[str, OptionValue]]]:
    views: list[tuple[str, str, dict[str, OptionValue]]] = [
        ("isla", "partybonus", {}),
        ("isla", "breakdown", {}),
    ]
    for handle, name in [("isla", "Ioseph"), ("kit", "Kael"), ("cora", "Crateris"),
                         ("cole", "Chris"), ("maya", "Mira")]:  # fmt: skip
        views.append((handle, "breakdown", {"character": name}))
        views.append((handle, "mybonus", {"character": name}))
    return views


@M4
@pytest.mark.req("OUT-7")
@pytest.mark.parametrize(("handle", "command", "options"), _pronoun_views())
async def test_output_never_uses_pronouns_for_characters(
    make_world: MakeWorld, handle: str, command: str, options: dict[str, OptionValue]
) -> None:
    world = await make_world("sample-game")
    reply = await world.run(handle, command, **options)

    assert str(options.get("character", "Ioseph")) in reply.text
    found = PRONOUNS.findall(reply.text)
    assert not found, f"pronouns in /{command}: {found}"


# ---------------------------------------------------------------- OUT-9: /help


def _next_step(text: str) -> str:
    """The last paragraph of a reply: where /help gives the player's next step (OUT-9).

    Code-block fences are ignored, so the layout is free to use them.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.replace("```", "")) if p.strip()]
    assert paragraphs, "the reply is empty"
    return paragraphs[-1]


@M6
@pytest.mark.req("OUT-9", "OUT-5", "OUT-3b")
async def test_help_is_one_private_message(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("newbie", "help")
    assert "/partybonus" in reply.text, "the guide itself, not a refusal"
    assert reply.private
    assert len(reply.messages) == 1
    assert len(reply.messages[0]) <= 2000


@M6
@pytest.mark.req("OUT-9")
async def test_help_names_the_setup_commands(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    text = (await world.run("craig", "help")).text
    for command in ["/character register", "/guild join", "/add", "/catalog", "/request"]:
        assert command in text, f"{command} is missing"
    assert "Support" in text, "Support comes from the Guild rank roles, with nothing to add"


@M6
@pytest.mark.req("OUT-9")
async def test_help_names_the_game_night_commands(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    text = (await world.run("craig", "help")).text
    for command in ["/sitout", "/sitin", "/partybonus", "/mybonus", "/breakdown"]:
        assert command in text, f"{command} is missing"
    assert "voice channel" in text.casefold(), "being in voice is how players are counted"


@M6
@pytest.mark.req("OUT-9", "CH-3")
async def test_help_tells_players_with_several_characters_about_play(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "help")
    assert "/play" in reply.text
    assert "/play" not in _next_step(reply.text), "craig is set up: /play is the general note"


@M6
@pytest.mark.req("OUT-9", "CH-1")
async def test_help_tells_a_player_with_no_character_to_register_one(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    step = _next_step((await world.run("newbie", "help")).text)
    assert "/character register" in step


@M6
@pytest.mark.req("OUT-9", "CH-3")
async def test_help_tells_a_player_with_no_current_character_to_play_one(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    await world.set_current("craig", None)
    step = _next_step((await world.run("craig", "help")).text)
    assert "/play" in step
    assert "/character register" not in step


@M6
@pytest.mark.req("OUT-9", "HV-1")
async def test_help_tells_a_player_to_add_what_a_new_character_has(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    await world.run("newbie", "character register", name="Pip")
    step = _next_step((await world.run("newbie", "help")).text)
    assert "/add" in step
    assert "Pip" in step
    assert "/character register" not in step


@M6
@pytest.mark.req("OUT-9")
async def test_help_tells_a_set_up_player_how_to_see_the_bonuses(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    step = _next_step((await world.run("craig", "help")).text)
    assert "/partybonus" in step
    for other in ["/character register", "/add", "/play"]:
        assert other not in step, f"craig is set up; the next step isn't {other}"


@M7
@pytest.mark.req("DOC-6", "OUT-9", "DOC-1")
async def test_help_links_to_the_documentation_site_near_the_top(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    for handle in ["newbie", "craig"]:
        reply = await world.run(handle, "help")
        paragraphs = [p for p in re.split(r"\n\s*\n", reply.text.replace("```", "")) if p.strip()]
        assert "https://dochavok.github.io/awt_party_bonus_bot/" in paragraphs[0]
        assert len(reply.messages) == 1
        assert "github.io" not in _next_step(reply.text), "the next step stays at the end"
