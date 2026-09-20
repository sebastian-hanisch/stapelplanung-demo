import pytest

import stk_constants as C
from stk_evaluation import (RuleOutcome, SweepResult, best_rule, compare_rules, comparison_rows, information_value,
                            outcome_of, savings, sigma_sweep, tipping_point, verdict, vs_optimum)
from stk_exact import ExactResult, solve_exact
from stk_scenario import generate_instance
from stk_simulation import Result, run_rule


def _result(moves, retrievals=10, with_move=None, max_h=3):
    with_move = min(retrievals, moves) if with_move is None else with_move
    return Result(moves, retrievals, with_move, max_h, tuple(range(moves)), ())


def _outcomes(**moves):
    """RuleOutcomes mit vorgegebenen Umstapelzahlen: _outcomes(niedrigster_stapel=5, bestfit=3, ...)"""
    return tuple(RuleOutcome(k, C.RULE_LABELS[k], _result(moves[k])) for k in C.RULE_KEYS)


def _sweep(sigmas, **per_rule):
    """SweepResult aus Werten je Regel und sigma; ein Wert = eine Instanz, Tupel = mehrere Instanzen."""
    values = {}
    for k in C.RULE_KEYS:
        seq = per_rule.get(k, [0.5] * len(sigmas))
        values[k] = tuple(v if isinstance(v, tuple) else (v,) for v in seq)
    n = len(next(iter(values.values()))[0])
    return SweepResult(tuple(sigmas), n, values)


# ---------- Vergleich auf einer Instanz ----------
def test_compare_rules_matches_direct_runs():
    inst = generate_instance(6, 5, 0.8, 60, 1)
    outcomes = compare_rules(inst, 0.25)
    assert [o.key for o in outcomes] == list(C.RULE_KEYS)
    assert [o.label for o in outcomes] == [C.RULE_LABELS[k] for k in C.RULE_KEYS]
    for o in outcomes:
        assert o.moves == run_rule(inst, o.key, 0.25).moves
        assert len(o.result.steps) == inst.n_events              # Verlauf aufgezeichnet
    assert [o.moves for o in outcomes] == [20, 6, 5, 2]           # feste Werte aus der Messreihe


def test_best_rule_takes_fewest_moves():
    o = _outcomes(zufaellig=9, niedrigster_stapel=5, bestfit=3, unsicherheitsbewusst=4)
    assert best_rule(o).key == C.RULE_BESTFIT


def test_best_rule_tie_prefers_baseline_then_bestfit_then_aware():
    assert best_rule(_outcomes(zufaellig=9, niedrigster_stapel=3, bestfit=3, unsicherheitsbewusst=3)).key == C.BASELINE_RULE
    assert best_rule(_outcomes(zufaellig=9, niedrigster_stapel=5, bestfit=3, unsicherheitsbewusst=3)).key == C.RULE_BESTFIT
    assert best_rule(_outcomes(zufaellig=3, niedrigster_stapel=5, bestfit=4, unsicherheitsbewusst=3)).key == C.RULE_AWARE
    assert best_rule(_outcomes(zufaellig=3, niedrigster_stapel=5, bestfit=4, unsicherheitsbewusst=4)).key == C.RULE_RANDOM


def test_savings_never_negative_and_zero_when_baseline_is_best():
    s = savings(_outcomes(zufaellig=9, niedrigster_stapel=8, bestfit=2, unsicherheitsbewusst=4))
    assert (s.baseline_moves, s.best_moves, s.saved) == (8, 2, 6) and s.saved_pct == pytest.approx(75.0)
    s = savings(_outcomes(zufaellig=9, niedrigster_stapel=3, bestfit=6, unsicherheitsbewusst=4))
    assert s.saved == 0 and s.saved_pct == 0.0                       # Alltagsregel ist die beste -> keine Ersparnis
    s = savings(_outcomes(zufaellig=1, niedrigster_stapel=0, bestfit=0, unsicherheitsbewusst=0))
    assert s.saved == 0 and s.saved_pct == 0.0                       # Basis 0: keine Division durch null


def test_comparison_rows_delta_is_mine_minus_reference():
    o = _outcomes(zufaellig=9, niedrigster_stapel=5, bestfit=3, unsicherheitsbewusst=6)
    rows = {r.key: r for r in comparison_rows(o)}
    assert rows[C.RULE_LOWEST].delta_moves == 0 and rows[C.RULE_LOWEST].delta_per_container == 0
    assert rows[C.RULE_BESTFIT].delta_moves == -2                     # besser als die Alltagsregel -> negativ
    assert rows[C.RULE_BESTFIT].delta_per_container == pytest.approx(-0.2)
    assert rows[C.RULE_RANDOM].delta_moves == 4
    assert rows[C.RULE_AWARE].moves_per_container == pytest.approx(0.6)


def test_comparison_rows_carry_result_metrics():
    inst = generate_instance(5, 4, 0.8, 50, 2)
    o = compare_rules(inst, 0.5)
    for row, out in zip(comparison_rows(o), o):
        assert row.share_with_move == out.result.share_retrievals_with_move
        assert row.max_stack_height == out.result.max_stack_height <= inst.max_height


def test_outcome_of():
    o = _outcomes(zufaellig=1, niedrigster_stapel=2, bestfit=3, unsicherheitsbewusst=4)
    assert outcome_of(o, C.RULE_BESTFIT).moves == 3


# ---------- Abstand zum Optimum ----------
def test_vs_optimum_proven_and_interval():
    o = _outcomes(zufaellig=9, niedrigster_stapel=6, bestfit=4, unsicherheitsbewusst=3)
    proven = ExactResult(2, 2, 5, 100, 0.1, None)
    rows = {r.key: r for r in vs_optimum(o, proven)}
    assert rows[C.RULE_BESTFIT].gap == 2 and rows[C.RULE_BESTFIT].ratio == pytest.approx(2.0)
    assert (rows[C.RULE_BESTFIT].gap_low, rows[C.RULE_BESTFIT].gap_high) == (4 - 5, 4 - 2)
    interval = ExactResult(None, 1, 5, 100, 10.0, "Zeitlimit")
    rows = {r.key: r for r in vs_optimum(o, interval)}
    assert rows[C.RULE_BESTFIT].gap is None and rows[C.RULE_BESTFIT].ratio is None
    assert (rows[C.RULE_BESTFIT].gap_low, rows[C.RULE_BESTFIT].gap_high) == (-1, 3)
    zero = ExactResult(0, 0, 0, 1, 0.0, None)
    assert vs_optimum(o, zero)[0].ratio is None                      # kein Quotient durch 0


def test_vs_optimum_with_real_exact_result_is_consistent():
    inst = generate_instance(4, 4, 1.0, 30, 7)                      # Optimum 2
    exact = solve_exact(inst, time_limit=60)
    for r in vs_optimum(compare_rules(inst, 0.5), exact):
        assert r.gap >= 0 and r.gap_low <= r.gap <= r.gap_high


# ---------- σ-Kurve ----------
def test_sweep_shape_grid_and_determinism():
    a = sigma_sweep(4, 3, 0.8, 30, 0.3, n_instances=5)
    assert a.sigmas == tuple(sorted(set(C.SWEEP_SIGMAS) | {0.3}))    # eingestelltes sigma ist im Raster
    assert a.n_instances == 5
    assert set(a.values) == set(C.RULE_KEYS)
    assert all(len(a.values[k]) == len(a.sigmas) and all(len(t) == 5 for t in a.values[k]) for k in C.RULE_KEYS)
    assert a == sigma_sweep(4, 3, 0.8, 30, 0.3, n_instances=5)


def test_sweep_grid_does_not_duplicate_a_sigma_already_in_it():
    a = sigma_sweep(4, 3, 0.8, 20, 0.5, n_instances=3)
    assert a.sigmas == C.SWEEP_SIGMAS


def test_sweep_values_equal_direct_runs_on_seeds_zero_to_n_minus_one():
    sw = sigma_sweep(5, 4, 0.8, 40, 0.5, n_instances=4)
    i = sw.index_of(0.5)
    for key in C.RULE_KEYS:
        for seed in range(4):
            inst = generate_instance(5, 4, 0.8, 40, seed)
            assert sw.series(key, i)[seed] == run_rule(inst, key, 0.5).moves_per_container


def test_sweep_mean_sem_and_paired_diff():
    sw = _sweep((0.0,), bestfit=[(1.0, 2.0, 3.0)], niedrigster_stapel=[(2.0, 4.0, 4.0)])
    assert sw.mean(C.RULE_BESTFIT, 0) == pytest.approx(2.0)
    assert sw.sem(C.RULE_BESTFIT, 0) == pytest.approx(1 / 3 ** 0.5)      # stdev 1, n 3
    mean, se = sw.paired_diff(C.RULE_BESTFIT, C.RULE_LOWEST, 0)          # Differenzen -1, -2, -1
    assert mean == pytest.approx(-4 / 3)
    assert se == pytest.approx((1 / 3) ** 0.5 / 3 ** 0.5)               # stdev der Differenzen = sqrt(1/3)


def test_sweep_index_of_picks_nearest_grid_point():
    sw = _sweep((0.0, 0.5, 1.0))
    assert sw.index_of(0.4) == 1 and sw.index_of(0.9) == 2 and sw.index_of(0.0) == 0


# Feste Werte aus der Planseite (Block 6x5, Füllgrad 0,8, 200 Container, 60 Instanzen)
def test_sweep_reproduces_measured_curve():
    sw = sigma_sweep(6, 5, 0.8, 200, 0.5, n_instances=60)
    z, last = 0, len(sw.sigmas) - 1
    expected = {
        C.RULE_RANDOM: (0.725, 1.006), C.RULE_LOWEST: (0.621, 0.845),
        C.RULE_BESTFIT: (0.239, 0.890), C.RULE_AWARE: (0.302, 0.839),
    }
    for key, (at_zero, at_two) in expected.items():
        assert round(sw.mean(key, z), 3) == at_zero, key
        assert round(sw.mean(key, last), 3) == at_two, key
    assert tipping_point(sw) == pytest.approx(1.3906, abs=1e-3)


# ---------- Kipppunkt ----------
def test_tipping_point_interpolates_the_sign_change():
    # Differenz (Bestfit - Niedrigster): -0.2 bei 0, -0.1 bei 0.5, +0.1 bei 1.0 -> Nullstelle bei 0.5 + 0.5 * 0.1/0.2 = 0.75
    sw = _sweep((0.0, 0.5, 1.0), bestfit=[0.3, 0.4, 0.6], niedrigster_stapel=[0.5, 0.5, 0.5])
    assert tipping_point(sw) == pytest.approx(0.75)


def test_tipping_point_none_when_trust_always_wins():
    sw = _sweep((0.0, 0.5, 1.0), bestfit=[0.1, 0.2, 0.3], niedrigster_stapel=[0.5, 0.5, 0.5])
    assert tipping_point(sw) is None


def test_tipping_point_zero_when_trust_never_better():
    sw = _sweep((0.0, 0.5), bestfit=[0.6, 0.7], niedrigster_stapel=[0.5, 0.5])
    assert tipping_point(sw) == 0.0


def test_tipping_point_equality_counts_as_tipped():
    sw = _sweep((0.0, 0.5, 1.0), bestfit=[0.3, 0.5, 0.7], niedrigster_stapel=[0.5, 0.5, 0.5])
    assert tipping_point(sw) == pytest.approx(0.5)


# ---------- Wert der Information ----------
def test_information_value():
    sw = _sweep((0.0, 0.5, 1.0), zufaellig=[0.8, 0.8, 0.8], bestfit=[0.2, 0.4, 0.7])
    v = information_value(sw, 0.5)
    assert v.at_zero == pytest.approx(0.6) and v.at_zero_factor == pytest.approx(4.0)
    assert v.at_sigma == pytest.approx(0.4) and v.at_sigma_factor == pytest.approx(2.0)
    assert information_value(sw, 0.0).at_sigma == pytest.approx(0.6)


def test_information_value_factor_none_when_bestfit_needs_no_moves():
    sw = _sweep((0.0, 1.0), zufaellig=[0.8, 0.8], bestfit=[0.0, 0.5])
    v = information_value(sw, 0.0)
    assert v.at_zero_factor is None and v.at_zero == pytest.approx(0.8)


# ---------- Urteil ----------
def _verdict_sweep(bestfit, lowest, aware=(0.9, 0.9, 0.9, 0.9)):
    return _sweep((0.0,), bestfit=[bestfit], niedrigster_stapel=[lowest], unsicherheitsbewusst=[aware], zufaellig=[(1.0,) * 4])


def test_verdict_trust_when_clearly_better():
    v = verdict(_verdict_sweep((0.2, 0.3, 0.25, 0.3), (0.5, 0.6, 0.55, 0.6)), 0.0)
    assert v.kind == "trust" and v.diff < 0 and v.saving_pct == pytest.approx(100 * 0.3 / 0.5625, rel=1e-6)
    assert v.best_mean_rule == C.RULE_BESTFIT and not v.aware_is_best


def test_verdict_tipped_when_clearly_worse():
    v = verdict(_verdict_sweep((0.7, 0.8, 0.75, 0.8), (0.5, 0.6, 0.55, 0.6)), 0.0)
    assert v.kind == "tipped" and v.diff > 0 and v.saving_pct < 0


def test_verdict_unclear_when_difference_is_within_noise():
    v = verdict(_verdict_sweep((0.6, 0.5, 0.6, 0.5), (0.5, 0.6, 0.5, 0.6)), 0.0)        # Differenzen +.1 -.1 +.1 -.1
    assert v.kind == "unclear" and v.diff == pytest.approx(0.0)


def test_verdict_unclear_when_identical():
    v = verdict(_verdict_sweep((0.5, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5)), 0.0)
    assert v.kind == "unclear" and v.se == 0.0


def test_verdict_reports_when_aware_rule_is_best():
    v = verdict(_verdict_sweep((0.7, 0.8, 0.75, 0.8), (0.5, 0.6, 0.55, 0.6), aware=(0.2, 0.3, 0.25, 0.3)), 0.0)
    assert v.aware_is_best and v.best_mean_rule == C.RULE_AWARE and v.kind == "tipped"


def test_verdict_on_real_data_follows_the_measured_pattern():
    sw = sigma_sweep(6, 5, 0.6, 120, 0.25, n_instances=30)
    assert verdict(sw, 0.25).kind == "trust"                                    # gute Schätzung: Bestfit klar besser
    sw_hi = sigma_sweep(6, 5, 0.6, 120, 2.0, n_instances=30)
    assert verdict(sw_hi, 2.0).kind == "tipped"                                 # sehr schlechte Schätzung: Ausgleich besser
    assert 0.5 < tipping_point(sw_hi) < 1.0                                    # Kipppunkt bei etwa 0,75


def test_verdict_small_nonzero_difference_inside_noise_is_unclear():
    # Differenzen +0.05, -0.15, +0.10, -0.10: Mittel -0.025, Standardfehler ~0.06 -> weit unter 2 Standardfehlern
    v = verdict(_verdict_sweep((0.55, 0.45, 0.60, 0.50), (0.5, 0.6, 0.5, 0.6)), 0.0)
    assert v.diff == pytest.approx(-0.025) and abs(v.diff) < C.VERDICT_Z * v.se
    assert v.kind == "unclear"


def test_verdict_just_beyond_two_standard_errors_is_clear():
    v = verdict(_verdict_sweep((0.40, 0.48, 0.42, 0.49), (0.5, 0.6, 0.5, 0.6)), 0.0)   # Differenzen -0.10 -0.12 -0.08 -0.11
    assert abs(v.diff) > C.VERDICT_Z * v.se and v.kind == "trust"
