"""The section 9 worked examples are requirements (TF-3): 9.1 and 9.2.

They're read from the `### 9.N` headings, so a new worked example is traced
without changing the harness.
"""

import pytest

from tests.support.coverage import TaggedTest, render
from tests.support.traceability import requirements

pytestmark = pytest.mark.milestone("M1")


@pytest.mark.req("TF-3", "9.1", "9.2")
def test_every_section_9_example_is_a_must_have_requirement() -> None:
    reqs = requirements()
    examples = {req_id for req_id in reqs if req_id.startswith("9.")}
    assert {"9.1", "9.2"} <= examples
    assert reqs["9.1"].text == "Sample game (section 9.1)"
    assert reqs["9.2"].text == "Item class game (section 9.2)"
    assert {reqs[e].priority for e in examples} == {"M"}


@pytest.mark.req("TF-3")
def test_the_coverage_table_lists_the_examples_after_the_rules_in_order() -> None:
    tests = [TaggedTest("tests/a.py::test_a", "M1", ("CH-1", "9.2", "4.15", "9.1", "4.2"), ())]
    text = render(tests)
    order = [text.index(f"| {req_id} |") for req_id in ["4.2", "4.15", "9.1", "9.2", "CH-1"]]
    assert order == sorted(order)
