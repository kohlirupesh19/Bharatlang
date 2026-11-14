"""Scoring rules and statistics of scripts/bench_score.py (the deployment benchmark)."""
import importlib.util
import math
from pathlib import Path

import pytest

pytest.importorskip("jiwer", reason="eval-only dependency (requirements-eval.txt)")

_SPEC = importlib.util.spec_from_file_location(
    "bench_score", Path(__file__).resolve().parents[2] / "scripts" / "bench_score.py")
bench = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bench)

REFUSAL = "उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत."


def rec(answer, expected, **kw):
    return {"answer": answer, "expected": expected, "error": None, "unverified_numbers": [],
            "abstention_reason": None, "answer_language": "mr", **kw}


def test_answerable_needs_every_figure_in_any_digit_script():
    assert bench.score(rec("हप्ता ₹८१७.५० प्रति हेक्टर", ["817.5"]))["correct"]
    assert not bench.score(rec("2017-18 आणि 2018-19", ["2017", "2018", "2019"]))["correct"]


@pytest.mark.parametrize("text,figure", [("रु. 50 हजार पर्यंत", "50000"), ("₹५० हजार", "50000"),
                                         ("२ लाख रुपये", "200000"), ("1.5 लाख", "150000")])
def test_number_words_are_expanded(text, figure):
    assert figure in bench.answer_numbers(text)


def test_language_counted_only_on_generated_answers():
    s = bench.score(rec(REFUSAL, None, answer_language=None, abstention_reason="gate"))
    assert not s["generated"]


def test_refusal_on_answerable_is_wrong_and_counted():
    s = bench.score(rec(REFUSAL, ["61000"]))
    assert not s["correct"] and s["refused"]


def test_trap_correct_only_when_refused_without_invented_numbers():
    assert bench.score(rec(REFUSAL, None))["correct"]
    assert bench.score(rec("काहीही", None, abstention_reason="gate"))["correct"]
    assert not bench.score(rec("हप्ता ₹500", None))["correct"]
    assert not bench.score(rec(REFUSAL + " ₹500", None, unverified_numbers=["500"]))["correct"]


def test_request_error_is_incorrect():
    assert not bench.score({"error": "ReadTimeout", "expected": ["1"]})["correct"]


def test_wilson_interval():
    lo, hi = bench.wilson(8, 10)
    assert lo == pytest.approx(0.490, abs=1e-3) and hi == pytest.approx(0.943, abs=1e-3)
    assert math.isnan(bench.wilson(0, 0)[0])


@pytest.mark.parametrize("b,c,p", [(0, 0, 1.0), (5, 5, 1.0), (10, 0, 2 / 1024), (1, 6, 0.125)])
def test_mcnemar_exact(b, c, p):
    assert bench.mcnemar_exact(b, c) == pytest.approx(p)


def test_paired_counts_discordant_pairs():
    def r(target, item, repeat, ok):
        return {**rec("61000" if ok else "x", ["61000"]), "target": target, "kind": "text",
                "item": item, "repeat": repeat}
    records = [r("a", "q", 1, True), r("b", "q", 1, False), r("a", "q", 2, True), r("b", "q", 2, True)]
    p = bench.paired(records, ["a", "b"])["text"]
    assert (p["pairs"], p["only_a"], p["only_b"]) == (2, 1, 0)
