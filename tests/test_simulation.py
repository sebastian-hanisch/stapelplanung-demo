import pytest

import stk_constants as C
from stk_rules import RELOCATION_RULE, bestfit
from helpers import manual_instance as _instance
from stk_scenario import estimate_departures, generate_instance
from stk_simulation import run, run_rule


def _always(index):
    return lambda stacks, H, e_own, est, exclude=None: index


# ---------- Handfälle ----------
def test_hand_case_blocker_has_to_move():
    inst = _instance([("A", 0), ("A", 1), ("D", 0), ("D", 1)], 2, 2)
    r = run(inst, {c: float(d) for c, d in inst.departure.items()}, _always(0))
    assert r.moves == 1 and r.retrievals == 2 and r.retrievals_with_move == 1
    assert r.cumulative == (0, 0, 1, 1)


def test_hand_case_lifo_needs_no_move():
    inst = _instance([("A", 0), ("A", 1), ("A", 2), ("D", 2), ("D", 1), ("D", 0)], 2, 3)
    assert run(inst, {c: float(d) for c, d in inst.departure.items()}, _always(0)).moves == 0


def test_hand_case_two_blockers_land_together():
    inst = _instance([("A", 0), ("A", 1), ("A", 2), ("D", 0), ("D", 1), ("D", 2)], 2, 3)
    r = run(inst, {c: float(d) for c, d in inst.departure.items()}, _always(0), record=True)
    assert r.moves == 2 and r.retrievals_with_move == 1
    step = r.steps[3]                                  # Abholung von 0
    assert step.moved == (2, 1)                        # oberster zuerst
    assert step.stacks == ((), (2, 1))                 # beide in Stapel 1, dort schon richtig herum
    assert r.max_stack_height == 3


# ---------- Referenzwerte aus der Messreihe ----------
PINS = {
    (6, 5, 0.8, 60, 1, 0.25): dict(n_events=120, dwell=9.3, zufaellig=20, niedrigster_stapel=6, bestfit=5, unsicherheitsbewusst=2),
    (4, 4, 1.0, 30, 0, 0.0): dict(n_events=60, dwell=5.133333, zufaellig=7, niedrigster_stapel=2, bestfit=0, unsicherheitsbewusst=0),
    (3, 3, 1.0, 14, 2, 0.5): dict(n_events=28, dwell=6.285714, zufaellig=6, niedrigster_stapel=4, bestfit=2, unsicherheitsbewusst=1),
    (5, 4, 0.6, 50, 7, 1.0): dict(n_events=100, dwell=15.24, zufaellig=41, niedrigster_stapel=19, bestfit=26, unsicherheitsbewusst=15),
    (6, 5, 1.0, 80, 3, 0.1): dict(n_events=160, dwell=11.875, zufaellig=23, niedrigster_stapel=11, bestfit=4, unsicherheitsbewusst=2),
}


@pytest.mark.parametrize("params", list(PINS))
def test_reproduces_measured_reference_numbers(params):
    S, H, fill, n, seed, sigma = params
    pin = PINS[params]
    inst = generate_instance(S, H, fill, n, seed)
    assert inst.n_events == pin["n_events"]
    assert round(inst.mean_dwell, 6) == pin["dwell"]
    for key in C.RULE_KEYS:
        assert run_rule(inst, key, sigma).moves == pin[key], key


# ---------- Invarianten über viele Instanzen ----------
CASES = [(3, 3, 1.0, 40, 0), (4, 4, 1.0, 60, 1), (6, 5, 0.8, 80, 2), (6, 5, 0.4, 50, 3), (8, 3, 1.0, 70, 4), (2, 6, 1.0, 30, 5)]


@pytest.mark.parametrize("S,H,fill,n,seed", CASES)
@pytest.mark.parametrize("rule_key", C.RULE_KEYS)
@pytest.mark.parametrize("sigma", [0.0, 0.5, 2.0])
def test_every_step_is_consistent(S, H, fill, n, seed, rule_key, sigma):
    inst = generate_instance(S, H, fill, n, seed)
    res = run_rule(inst, rule_key, sigma, record=True)
    assert len(res.steps) == inst.n_events == len(res.cumulative)

    prev_stacks = tuple(() for _ in range(S))
    present, total = set(), 0
    for idx, (step, (kind, c)) in enumerate(zip(res.steps, inst.events)):
        assert (step.kind, step.container) == (kind, c)
        assert all(len(s) <= H for s in step.stacks)
        now = {x for s in step.stacks for x in s}
        assert sum(len(s) for s in step.stacks) == len(now)          # kein Container doppelt
        if kind == "A":
            present.add(c)
            assert step.moved == () and step.stacks[step.stack][-1] == c
        else:
            present.remove(c)
            x = step.stack
            above = tuple(reversed(prev_stacks[x][prev_stacks[x].index(c) + 1:]))
            assert step.moved == above                                # genau die Container über dem Ziel
            assert all(m not in step.stacks[x] for m in step.moved)   # und sie sind nicht im Ursprungsstapel geblieben
            total += len(step.moved)
        assert now == present                                         # nichts geht verloren, nichts kommt dazu
        assert len(now) <= inst.capacity
        assert step.moves_so_far == total == res.cumulative[idx]
        prev_stacks = step.stacks

    assert res.moves == total == res.cumulative[-1]
    assert list(res.cumulative) == sorted(res.cumulative)             # monoton
    assert res.retrievals == n and 0 <= res.retrievals_with_move <= n
    assert res.retrievals_with_move <= res.moves
    assert prev_stacks == tuple(() for _ in range(S))                 # am Ende leer


def test_recording_does_not_change_the_numbers():
    inst = generate_instance(6, 5, 0.8, 100, 9)
    for key in C.RULE_KEYS:
        a, b = run_rule(inst, key, 0.5), run_rule(inst, key, 0.5, record=True)
        assert (a.moves, a.cumulative, a.retrievals_with_move, a.max_stack_height) == \
               (b.moves, b.cumulative, b.retrievals_with_move, b.max_stack_height)
        assert a.steps == ()


# ---------- unabhängiges Kontrollmodell ----------
def _reference_moves(inst, est, place):
    """Bewusst anders geschrieben als stk_simulation.run: Blocker werden als Scheibe abgehoben."""
    stacks = [[] for _ in range(inst.n_stacks)]
    moves = 0
    for kind, c in inst.events:
        if kind == "A":
            stacks[place(stacks, inst.max_height, est[c], est)].append(c)
            continue
        x = next(i for i, s in enumerate(stacks) if c in s)
        pos = stacks[x].index(c)
        blockers = stacks[x][pos + 1:]
        del stacks[x][pos:]                                   # Ziel und alles darüber weg
        for b in reversed(blockers):
            stacks[RELOCATION_RULE(stacks, inst.max_height, est[b], est, exclude=x)].append(b)
            moves += 1
    return moves


@pytest.mark.parametrize("S,H,fill,n,seed", CASES)
def test_matches_independent_reference_model(S, H, fill, n, seed):
    inst = generate_instance(S, H, fill, n, seed)
    est = estimate_departures(inst, 0.5)
    for place in (bestfit, lambda st, h, e, es, exclude=None: min((i for i, s in enumerate(st) if len(s) < h), key=lambda i: (len(st[i]), i))):
        assert run(inst, est, place).moves == _reference_moves(inst, est, place)


def test_sigma_zero_bestfit_beats_random_on_average():
    """Kernaussage der Demo, grob: mit exakter Abfahrtskenntnis sind viel weniger Umstapelungen nötig."""
    tot_rand = tot_best = 0
    for seed in range(20):
        inst = generate_instance(6, 5, 0.8, 100, seed)
        tot_rand += run_rule(inst, C.RULE_RANDOM, 0.0).moves
        tot_best += run_rule(inst, C.RULE_BESTFIT, 0.0).moves
    assert tot_best * 2.5 < tot_rand


def test_run_rule_random_is_reproducible():
    inst = generate_instance(5, 4, 0.8, 60, 4)
    assert run_rule(inst, C.RULE_RANDOM, 0.3).moves == run_rule(inst, C.RULE_RANDOM, 0.3).moves


def test_max_stack_height_counts_relocation_targets():
    # Stapel 1 = [0, 1], Stapel 0 = [2, 3]. Abholung von 2 hebt 3 auf Stapel 1: dort Höhe 3, vorher war 2 das Maximum.
    events = [("A", 0), ("A", 1), ("A", 2), ("A", 3), ("D", 2), ("D", 3), ("D", 1), ("D", 0)]
    inst = _instance(events, 2, 3)
    target = {0: 1, 1: 1, 2: 0, 3: 0}
    place = lambda stacks, H, e_own, est, exclude=None: target[next(c for c in target if est[c] == e_own)]
    r = run(inst, {c: float(d) for c, d in inst.departure.items()}, place, record=True)
    assert r.moves == 1
    assert max(len(s) for s in r.steps[3].stacks) == 2      # nach den Ankünften höchstens 2
    assert r.max_stack_height == 3                          # erst das Umstapeln macht 3
