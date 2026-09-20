import pytest

import stk_constants as C
from stk_rules import RELOCATION_RULE, bestfit, make_aware_rule, make_random_rule, make_rule, niedrigster_stapel

H = 3


# ---------- bestfit ----------
def test_bestfit_takes_tightest_non_blocking_stack():
    # oberste ê der Stapel: 50, 20, 30. Eigener Container ê=10 -> alle nicht blockierend, enger = 20
    stacks = [[0], [1], [2]]
    e = {0: 50, 1: 20, 2: 30}
    assert bestfit(stacks, H, 10, e) == 1


def test_bestfit_prefers_any_used_stack_over_empty():
    stacks = [[0], []]
    e = {0: 99}
    assert bestfit(stacks, H, 10, e) == 0


def test_bestfit_uses_empty_stack_if_all_others_would_be_blocked():
    stacks = [[0], [1], []]
    e = {0: 5, 1: 8}
    assert bestfit(stacks, H, 20, e) == 2


def test_bestfit_least_harm_when_everything_blocks():
    # kein leerer Stapel, alle oben früher fahrend -> der mit dem größten ê (am spätesten)
    stacks = [[0], [1], [2]]
    e = {0: 5, 1: 9, 2: 7}
    assert bestfit(stacks, H, 20, e) == 1


def test_bestfit_skips_full_and_excluded_stacks():
    stacks = [[0, 1, 2], [3], [4]]
    e = {0: 100, 1: 100, 2: 100, 3: 50, 4: 60}
    assert bestfit(stacks, H, 10, e) == 1                 # Stapel 0 voll
    assert bestfit(stacks, H, 10, e, exclude=1) == 2      # Stapel 1 ausgeschlossen


def test_bestfit_tie_goes_to_lowest_index():
    stacks = [[0], [1]]
    e = {0: 30, 1: 30}
    assert bestfit(stacks, H, 10, e) == 0


# ---------- niedrigster Stapel ----------
def test_lowest_picks_fewest_containers_and_ignores_estimates():
    stacks = [[0, 1], [2], [3, 4, 5]]
    assert niedrigster_stapel(stacks, H, 0, {i: 0 for i in range(6)}) == 1


def test_lowest_tie_goes_to_lowest_index_and_skips_full():
    stacks = [[0, 1, 2], [3], [4]]
    assert niedrigster_stapel(stacks, H, 0, {}) == 1
    assert niedrigster_stapel(stacks, H, 0, {}, exclude=1) == 2


# ---------- zufällig ----------
def test_random_is_reproducible_and_stays_in_candidates():
    stacks = [[0, 1, 2], [], [3], []]
    r1, r2 = make_random_rule(7), make_random_rule(7)
    seq1 = [r1(stacks, H, 0, {}, exclude=3) for _ in range(30)]
    seq2 = [r2(stacks, H, 0, {}, exclude=3) for _ in range(30)]
    assert seq1 == seq2
    assert set(seq1) <= {1, 2}                            # Stapel 0 voll, Stapel 3 ausgeschlossen
    assert len(set(seq1)) == 2                            # beide kommen vor


# ---------- unsicherheitsbewusst ----------
def test_aware_with_tiny_sigma_behaves_like_bestfit():
    stacks = [[0], [1], [2]]
    e = {0: 50, 1: 20, 2: 30}
    assert make_aware_rule(1e-6)(stacks, H, 10, e) == bestfit(stacks, H, 10, e) == 1


def test_aware_prefers_empty_stack_over_risky_ones():
    # eigenes ê=25: Stapel 0 (oben 24) blockiert mit P~0.5+, Stapel 1 leer -> P=0
    stacks = [[0], []]
    e = {0: 24}
    assert make_aware_rule(5.0)(stacks, H, 25, e) == 1


def test_aware_prefers_clearly_safe_stack_over_nearly_tied_risky_one():
    # Stapel 0: oben 26 (fast gleichzeitig, P~0.4), Stapel 1: oben 100 (sicher)
    stacks = [[0], [1]]
    e = {0: 26, 1: 100}
    assert make_aware_rule(10.0)(stacks, H, 25, e) == 1


def test_aware_high_sigma_falls_back_to_balancing():
    # bei riesigem sigma ist P ueberall ~0.5 -> zweites Kriterium: niedrigster Stapel
    stacks = [[0, 1], [2], [3, 4]]
    e = {i: 10 * i for i in range(5)}
    assert make_aware_rule(1e9)(stacks, H, 15, e) == 1


# ---------- gemeinsam ----------
@pytest.mark.parametrize("rule", [bestfit, niedrigster_stapel, make_random_rule(1), make_aware_rule(3.0)])
def test_all_rules_raise_when_no_free_stack(rule):
    stacks = [[0, 1, 2], [3, 4, 5]]
    with pytest.raises(ValueError):
        rule(stacks, H, 1.0, {i: float(i) for i in range(6)})
    with pytest.raises(ValueError):                       # einziger freier Stapel ausgeschlossen
        rule([[0, 1, 2], [3]], H, 1.0, {i: float(i) for i in range(4)}, exclude=1)


def test_relocation_rule_is_bestfit_for_every_rule():
    assert RELOCATION_RULE is bestfit


def test_make_rule_dispatch():
    assert make_rule(C.RULE_LOWEST) is niedrigster_stapel
    assert make_rule(C.RULE_BESTFIT) is bestfit
    assert callable(make_rule(C.RULE_RANDOM, seed=3))
    assert callable(make_rule(C.RULE_AWARE, sigma_abs=4.0))
    with pytest.raises(ValueError):
        make_rule("gibt_es_nicht")
    assert set(C.RULE_LABELS) == set(C.RULE_KEYS)
    assert C.BASELINE_RULE in C.RULE_KEYS


def test_bestfit_equal_estimate_counts_as_non_blocking():
    # Gleicher Abfahrtszeitpunkt blockiert nicht: ê_eigen == ê_oben zählt als "passt", und zwar am engsten.
    stacks = [[0], [1]]
    e = {0: 10, 1: 20}
    assert bestfit(stacks, H, 10, e) == 0
