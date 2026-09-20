"""Jedes Preset erzählt eine Geschichte (Abnahmekriterien aus dem Plan, Abschnitt 7). Hier wird geprüft, dass sie trägt:

1. am gewählten Seed (sonst zeigt das Preset das Gegenteil dessen, was sein Hilfetext sagt),
2. bei anderen Rausch-Ziehungen (Ereignis-Seed UND Rausch-Strom, sonst hängt die Aussage an einem Glückstreffer),
3. im MITTEL über viele Seeds (sonst ist das Preset ein Einzelfall, den man nach dem schönsten Seed ausgesucht hat).

Die Abstimmung selbst steht in tools/tune_presets.py."""

import statistics as st

import pytest

import stk_constants as C
from stk_exact import solve_exact
from stk_scenario import generate_instance
from stk_simulation import run_rule

NOISE_SEEDS = range(20)
POPULATION = range(60)


def _instance(preset, seed=None):
    p = C.PRESETS[preset]
    return generate_instance(p["n_stacks"], p["max_height"], p["fill_pct"] / 100, p["n_containers"], p["seed"] if seed is None else seed)


def _moves(inst, rule, sigma, noise_seed=None):
    return run_rule(inst, rule, sigma, noise_seed).moves


def _sigma(preset):
    return C.PRESETS[preset]["sigma_pct"] / 100


# ---------- Perfekte Info: exakte Kenntnis ist viel wert ----------
def test_perfect_info_random_needs_at_least_2_5_times_as_many_moves_as_bestfit():
    inst = _instance("Perfekte Info")
    best, rnd, low = (_moves(inst, r, 0.0) for r in (C.RULE_BESTFIT, C.RULE_RANDOM, C.RULE_LOWEST))
    assert best > 0 and rnd >= 2.5 * best and best < low


def test_perfect_info_holds_on_average():
    inst = [_instance("Perfekte Info", s) for s in POPULATION]
    best = st.fmean(_moves(i, C.RULE_BESTFIT, 0.0) for i in inst)
    rnd = st.fmean(_moves(i, C.RULE_RANDOM, 0.0) for i in inst)
    assert rnd >= 2.8 * best                                            # gemessen: ≈ 3,3 (Verhältnis der Mittel)
    assert all(_moves(i, C.RULE_BESTFIT, 0.0) < _moves(i, C.RULE_LOWEST, 0.0) for i in inst)     # gemessen: 100 % der Seeds


# ---------- Realistisch: der Vorsprung schrumpft, bleibt aber ----------
def test_realistic_bestfit_still_wins_but_by_less_than_with_perfect_information():
    inst = _instance("Realistisch")
    saving = lambda sigma: 1 - _moves(inst, C.RULE_BESTFIT, sigma) / _moves(inst, C.RULE_LOWEST, sigma)
    assert saving(_sigma("Realistisch")) > 0
    assert saving(_sigma("Realistisch")) < saving(0.0)


def test_realistic_is_stable_across_noise_draws():
    inst, sigma = _instance("Realistisch"), _sigma("Realistisch")
    wins = sum(_moves(inst, C.RULE_BESTFIT, sigma, ns) < _moves(inst, C.RULE_LOWEST, sigma, ns) for ns in NOISE_SEEDS)
    assert wins / len(NOISE_SEEDS) >= 0.9                               # gemessen: 100 %


def test_realistic_holds_on_average():
    sigma = _sigma("Realistisch")
    inst = [_instance("Realistisch", s) for s in POPULATION]
    wins = sum(_moves(i, C.RULE_BESTFIT, sigma) < _moves(i, C.RULE_LOWEST, sigma) for i in inst)
    assert wins / len(inst) >= 0.85                                     # gemessen: 94 % über 200 Seeds


# ---------- Kaum brauchbar: die simple Regel schlägt die schätzungsgläubige ----------
def test_barely_usable_the_simple_rule_beats_the_trusting_one():
    inst, sigma = _instance("Kaum brauchbar"), _sigma("Kaum brauchbar")
    assert _moves(inst, C.RULE_LOWEST, sigma) < _moves(inst, C.RULE_BESTFIT, sigma)


def test_barely_usable_is_stable_across_noise_draws():
    inst, sigma = _instance("Kaum brauchbar"), _sigma("Kaum brauchbar")
    wins = sum(_moves(inst, C.RULE_LOWEST, sigma, ns) < _moves(inst, C.RULE_BESTFIT, sigma, ns) for ns in NOISE_SEEDS)
    assert wins / len(NOISE_SEEDS) >= 0.9                               # gemessen: 95 %


def test_barely_usable_holds_on_average_and_information_is_worthless_there():
    sigma = _sigma("Kaum brauchbar")
    inst = [_instance("Kaum brauchbar", s) for s in POPULATION]
    wins = sum(_moves(i, C.RULE_LOWEST, sigma) < _moves(i, C.RULE_BESTFIT, sigma) for i in inst)
    assert wins / len(inst) >= 0.8                                      # gemessen: 90 % über 200 Seeds
    # der Schätzung zu trauen bringt hier kaum etwas gegenüber Zufall: Bestfit liegt näher an "zufällig" als am Ausgleich
    best = st.fmean(_moves(i, C.RULE_BESTFIT, sigma) for i in inst)
    rnd = st.fmean(_moves(i, C.RULE_RANDOM, sigma) for i in inst)
    low = st.fmean(_moves(i, C.RULE_LOWEST, sigma) for i in inst)
    assert best > low and rnd / best < 1.4


# ---------- Voller Block: auch mit Vorwissen bleibt viel Umstapeln ----------
def test_full_block_needs_clearly_more_moves_than_the_80_percent_block():
    full, part = _instance("Voller Block"), _instance("Perfekte Info")
    assert _moves(full, C.RULE_BESTFIT, 0.0) >= 1.5 * _moves(part, C.RULE_BESTFIT, 0.0)
    assert _moves(full, C.RULE_BESTFIT, 0.0) / C.PRESETS["Voller Block"]["n_containers"] >= 0.25


def test_full_block_holds_on_average():
    full = [_instance("Voller Block", s) for s in POPULATION]
    part = [_instance("Perfekte Info", s) for s in POPULATION]
    f = st.fmean(_moves(i, C.RULE_BESTFIT, 0.0) for i in full)
    p = st.fmean(_moves(i, C.RULE_BESTFIT, 0.0) for i in part)
    assert f >= 1.5 * p                                                 # gemessen: ≈ 1,85
    assert f / C.PRESETS["Voller Block"]["n_containers"] >= 0.3         # gemessen: 0,36 pro Container (nicht 0,5 wie bei N=200)


# ---------- Kleiner Block: exakt lösbar, Bestfit liegt etwa dreimal über dem Optimum ----------
def test_small_block_is_solved_exactly_quickly_and_bestfit_is_far_above_the_optimum():
    inst = _instance("Kleiner Block")
    r = solve_exact(inst, time_limit=10)
    assert r.proven and r.seconds < 3
    best = _moves(inst, C.RULE_BESTFIT, 0.0)
    assert r.optimum >= 2 and r.optimum < best and best >= 2 * r.optimum


def test_small_block_holds_on_average():
    ratios_best, ratios_opt = [], []
    for seed in range(30):
        inst = _instance("Kleiner Block", seed)
        r = solve_exact(inst, time_limit=10)
        assert r.proven
        ratios_best.append(_moves(inst, C.RULE_BESTFIT, 0.0))
        ratios_opt.append(r.optimum)
    assert st.fmean(ratios_best) / st.fmean(ratios_opt) >= 2.0          # gemessen: ≈ 2,9 über 100 Seeds
    assert all(b >= o for b, o in zip(ratios_best, ratios_opt))         # das Optimum ist nie schlechter


# ---------- gemeinsame Anforderungen ----------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_uses_a_seed_inside_the_slider_range(name):
    assert C.SEED_RANGE[0] <= C.PRESETS[name]["seed"] <= C.SEED_RANGE[1]


def test_default_scenario_equals_the_realistic_preset():
    """Wer die Seite öffnet, sieht das Preset 'Realistisch' (dieselben Regler, derselbe Seed)."""
    p = C.PRESETS["Realistisch"]
    assert (p["n_stacks"], p["max_height"], p["fill_pct"], p["n_containers"], p["sigma_pct"], p["seed"]) == (
        C.N_STACKS_DEFAULT, C.MAX_HEIGHT_DEFAULT, C.FILL_PCT_DEFAULT, C.N_CONTAINERS_DEFAULT, C.SIGMA_PCT_DEFAULT, C.SEED_DEFAULT)
