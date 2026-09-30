"""User documentation (requirements section 18: DOC-1 to DOC-7), milestone M7.

The interfaces these tests fix (TF-2): the site is configured in ``mkdocs.yml`` at the
repository root and built from ``docs/``; the command reference is
``docs/commands.md``; the maintainer guide is ``docs/maintainer.md``; and
``scripts/generate_docs.py`` regenerates every generated part of the docs, with
``--check`` (exit 1, naming each out-of-date file, without writing) and
``--docs <folder>`` (the docs folder to write or check, ``docs/`` by default).

Whether the pages say the right things is checked by reading them (DOC-2, see the
"Partly automated" table in tests/COVERAGE.md).
"""

import re
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import discord
import pytest
import yaml

from awt_bonus.bot import build_tree, intents
from tests.support.traceability import ROOT
from tests.support.world import MakeWorld, World

pytestmark = pytest.mark.milestone("M7")

DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"
GENERATOR = ROOT / "scripts" / "generate_docs.py"
WORKFLOWS = ROOT / ".github" / "workflows"
SITE_URL = "https://dochavok.github.io/awt_party_bonus_bot/"

# Maintainer documents: in the repository, never on the site (DOC-1, DOC-3).
MAINTAINER_DOCS = ["maintainer.md", "deployment.md", "restore-runbook.md", "test-server.md"]


class _AnyTagLoader(yaml.SafeLoader):
    """Safe loading that keeps unknown tags (e.g. mkdocs-material's !!python/name) as text."""


_AnyTagLoader.add_multi_constructor(
    "",
    lambda loader, suffix, node: (
        loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else None
    ),
)


def _mkdocs_config() -> dict[str, Any]:
    assert MKDOCS.exists(), "mkdocs.yml is missing (DOC-1)"
    config: dict[str, Any] = yaml.load(MKDOCS.read_text(encoding="utf-8"), _AnyTagLoader)  # noqa: S506
    return config


def _plugin_names(config: dict[str, Any]) -> list[str]:
    return [next(iter(p)) if isinstance(p, dict) else str(p) for p in config.get("plugins", [])]


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, timeout=300
    )


def _built_page(site: Path, page: Path) -> Path:
    """Where mkdocs puts a source page (directory URLs): a/b.md -> a/b/index.html."""
    relative = page.relative_to(DOCS).with_suffix("")
    if relative.name == "index":
        return site / relative.parent / "index.html"
    return site / relative / "index.html"


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The site, built once for this module with --strict (warnings are errors)."""
    folder = tmp_path_factory.mktemp("site")
    result = _run("-m", "mkdocs", "build", "--strict", "--site-dir", str(folder))
    assert result.returncode == 0, result.stdout + result.stderr
    return folder


def _site_pages(site: Path) -> list[Path]:
    """The source pages that are published on the site."""
    return [page for page in sorted(DOCS.rglob("*.md")) if _built_page(site, page).exists()]


def _front_matter(page: Path) -> dict[str, Any]:
    text = page.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        return {}
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------- DOC-1: the site


@pytest.mark.req("DOC-1")
def test_the_site_builds_without_warnings(site: Path) -> None:
    assert (site / "index.html").exists()


@pytest.mark.req("DOC-1")
def test_the_site_uses_material_with_search_at_the_github_pages_address() -> None:
    config = _mkdocs_config()
    theme = config.get("theme", {})
    assert (theme.get("name") if isinstance(theme, dict) else theme) == "material"
    assert config.get("site_url") == SITE_URL
    assert "search" in _plugin_names(config)


@pytest.mark.req("DOC-1")
def test_the_site_has_a_search_index(site: Path) -> None:
    assert (site / "search" / "search_index.json").exists()


@pytest.mark.req("DOC-1", "DOC-3")
@pytest.mark.parametrize("name", MAINTAINER_DOCS)
def test_maintainer_docs_arent_on_the_site(site: Path, name: str) -> None:
    source = DOCS / name
    assert source.exists(), f"docs/{name} should stay in the repository"
    assert not _built_page(site, source).exists(), f"docs/{name} is published on the site"
    assert f"/{source.stem}/" not in (site / "sitemap.xml").read_text(encoding="utf-8")


@pytest.mark.req("DOC-1")
def test_a_push_to_main_publishes_the_site() -> None:
    publishing = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        if "actions/deploy-pages" not in text:
            continue
        data = yaml.safe_load(text)
        # YAML 1.1 reads the key "on" as True.
        triggers = data.get("on", data.get(True))
        if "main" in str(triggers):
            publishing.append(workflow.name)
    assert publishing, "no workflow deploys the site to GitHub Pages from main"


# ---------------------------------------------------------------- DOC-2: the pages


@pytest.mark.req("DOC-2", "CT-9")
def test_a_player_page_explains_setting_up_and_requesting_missing_entries(site: Path) -> None:
    pages = [
        page
        for page in _site_pages(site)
        if "/character register" in (text := page.read_text(encoding="utf-8"))
        and "/request" in text
    ]
    assert pages, "no page covers setting up a character and /request together"


@pytest.mark.req("DOC-2", "AD-2")
def test_a_page_tells_dms_to_sit_out_and_check_the_breakdown(site: Path) -> None:
    pages = [
        page
        for page in _site_pages(site)
        if "DM" in (text := page.read_text(encoding="utf-8"))
        and "/sitout" in text
        and "/breakdown" in text
    ]
    assert pages, "no page for DMs running a game with the bot"


# ---------------------------------------------------------------- DOC-3: maintainer guide


@pytest.mark.req("DOC-3")
def test_the_maintainer_guide_links_the_steps_already_written_elsewhere() -> None:
    guide = DOCS / "maintainer.md"
    assert guide.exists()
    text = guide.read_text(encoding="utf-8")
    for linked in ["deployment.md", "restore-runbook.md", "catalog/README.md"]:
        assert linked in text, f"the maintainer guide doesn't link {linked}"


@pytest.mark.req("DOC-3", "CH-2", "HV-6", "CT-9")
def test_the_maintainer_guide_covers_each_kind_of_request() -> None:
    text = (DOCS / "maintainer.md").read_text(encoding="utf-8")
    assert "/request" in text
    for command in ["remove-character", "transfer", "remove-entry"]:
        assert command in text, f"the maintainer guide doesn't mention awt-admin {command}"


# ---------------------------------------------------------------- DOC-4, DOC-5: generated parts


@pytest.mark.req("DOC-4", "DOC-5")
def test_the_generated_docs_are_up_to_date() -> None:
    result = _run(str(GENERATOR), "--check")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.req("DOC-4", "DOC-5")
def test_the_check_names_an_out_of_date_generated_file(tmp_path: Path) -> None:
    before = _run(str(GENERATOR), "--check")
    assert before.returncode == 0, before.stdout + before.stderr
    copy = tmp_path / "docs"
    shutil.copytree(DOCS, copy)
    reference = copy / "commands.md"
    reference.write_text(
        reference.read_text(encoding="utf-8").replace("/partybonus", "/partybonuses"),
        encoding="utf-8",
    )

    result = _run(str(GENERATOR), "--check", "--docs", str(copy))

    assert result.returncode == 1
    assert "commands.md" in result.stdout + result.stderr
    assert "/partybonuses" in reference.read_text(encoding="utf-8"), "--check never writes"


@pytest.mark.req("DOC-4", "DOC-5")
def test_ci_runs_the_generated_docs_check() -> None:
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r"scripts/generate_docs\.py\s+--check", ci)


@pytest.mark.req("DOC-4", "TF-6")
def test_the_examples_dont_use_the_test_fixtures() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    assert "tests" not in re.sub(r"#.*", "", source), "the sample party is kept with the docs"


@pytest.mark.req("DOC-5", "OUT-5")
async def test_the_command_reference_lists_every_command_and_option(
    make_world: MakeWorld,
) -> None:
    world: World = await make_world("setup")
    client = discord.Client(intents=intents())
    guild = discord.Object(id=1)
    tree = build_tree(client, world.app, guild, world.settings)
    reference = DOCS / "commands.md"
    assert reference.exists()
    text = reference.read_text(encoding="utf-8")

    commands: list[discord.app_commands.Command[Any, ..., Any]] = []
    for command in tree.get_commands(guild=guild):
        if isinstance(command, discord.app_commands.Group):
            commands.extend(
                c for c in command.walk_commands() if not isinstance(c, discord.app_commands.Group)
            )
        elif isinstance(command, discord.app_commands.Command):
            commands.append(command)
    assert commands

    for command in commands:
        assert f"/{command.qualified_name}" in text, f"/{command.qualified_name} is missing"
        assert command.description in text, f"/{command.qualified_name}'s description"
        for parameter in command.parameters:
            assert parameter.name in text, f"/{command.qualified_name} {parameter.name}"
            if parameter.description != "…":
                assert parameter.description in text, (
                    f"/{command.qualified_name} {parameter.name}'s description"
                )


# ---------------------------------------------------------------- DOC-7: page dates


@pytest.mark.req("DOC-7")
def test_every_page_has_a_reviewed_date(site: Path) -> None:
    today = datetime.now(UTC).date()
    pages = _site_pages(site)
    assert pages
    for page in pages:
        reviewed = _front_matter(page).get("reviewed")
        name = page.relative_to(DOCS).as_posix()
        assert isinstance(reviewed, date), f"{name} has no reviewed: date in its front matter"
        assert reviewed <= today, f"{name} was reviewed in the future"


@pytest.mark.req("DOC-7")
def test_every_page_shows_when_it_was_updated_and_reviewed(site: Path) -> None:
    assert "git-revision-date-localized" in _plugin_names(_mkdocs_config())
    for page in _site_pages(site):
        reviewed = _front_matter(page).get("reviewed")
        html = _built_page(site, page).read_text(encoding="utf-8")
        name = page.relative_to(DOCS).as_posix()
        assert "git-revision-date-localized" in html, f"{name} doesn't show its updated date"
        assert isinstance(reviewed, date)
        assert reviewed.isoformat() in html, f"{name} doesn't show its reviewed date"
