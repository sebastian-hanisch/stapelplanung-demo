import sys

import pytest

import stk_constants as C
import stk_exact
from helpers import manual_instance
from stk_exact import ExactResult, blocking_lower_bound, solve_exact, stack_blockers
from stk_scenario import generate_instance
from stk_simulation import run_rule

INF = float("inf")


# ---------- unabhängiges Kontrollmodell: Vollaufzählung ohne Memo, Schranke und Symmetriebruch ----------
def brute_force_optimum(n_stacks, max_height, events):
    def go(i, stacks):
        if i == len(events):
            return 0
        kind, c = events[i]
        if kind == "A":
            best = INF
            for k in range(n_stacks):
                if len(stacks[k]) < max_height:
                    new = [list(s) for s in stacks]
                    new[k].append(c)
                    best = min(best, go(i + 1, new))
            return best
        x = next(k for k, s in enumerate(stacks) if c in s)
        pos = stacks[x].index(c)
        blockers = stacks[x][pos + 1:][::-1]
        base = [list(s) for s in stacks]
        base[x] = base[x][:pos + 1]
        best = INF

        def place(idx, cur):
            nonlocal best
            if idx == len(blockers):
                final = [list(s) for s in cur]
                final[x].pop()                                    # Ziel verlässt den Block
                best = min(best, len(blockers) + go(i + 1, final))
                return
            for k in range(n_stacks):
                if k != x and len(cur[k]) < max_height:
                    nxt = [list(s) for s in cur]
                    nxt[k].append(blockers[idx])
                    place(idx + 1, nxt)
        place(0, base)
        return best

    return go(0, [[] for _ in range(n_stacks)])


# ---------- Handfälle ----------
def _events(*items):
    return [(k, int(c)) for k, c in items]


def test_lifo_needs_no_relocation():
    inst = manual_instance(_events(("A", 0), ("A", 1), ("A", 2), ("D", 2), ("D", 1), ("D", 0)), 2, 3)
    r = solve_exact(inst)
    assert r.proven and r.optimum == 0


def test_two_stacks_separate_containers_needs_none():
    inst = manual_instance(_events(("A", 0), ("A", 1), ("D", 0), ("D", 1)), 2, 2)
    assert solve_exact(inst).optimum == 0


def test_three_increasing_departures_on_two_stacks_need_one_relocation():
    inst = manual_instance(_events(("A", 0), ("A", 1), ("A", 2), ("D", 0), ("D", 1), ("D", 2)), 2, 3)
    assert solve_exact(inst).optimum == 1
    inst3 = manual_instance(_events(("A", 0), ("A", 1), ("A", 2), ("D", 0), ("D", 1), ("D", 2)), 3, 3)
    assert solve_exact(inst3).optimum == 0


def test_blocking_lower_bound_hand_cases():
    d = {0: 5, 1: 9, 2: 1, 3: 3}
    assert blocking_lower_bound(((), ()), d) == 0
    assert blocking_lower_bound(((0, 1), (2,)), d) == 1            # 1 (d=9) liegt über 0 (d=5)
    assert blocking_lower_bound(((2, 0, 1),), d) == 2              # 0 und 1 liegen über 2 (d=1)
    assert blocking_lower_bound(((1, 0), (2, 3)), d) == 1          # 3 (d=3) über 2 (d=1); 0 (d=5) unter 1 (d=9) blockiert nicht
    # Entscheidend ist das FRÜHESTE unter allen tieferen Containern, nicht nur der direkt darunter:
    # unten d=1, Mitte d=5 (blockiert), oben d=3 (blockiert ebenfalls den Container unten, obwohl 3 < 5)
    assert blocking_lower_bound(((0, 1, 2),), {0: 1, 1: 5, 2: 3}) == 2


# ---------- Gegenprobe gegen die Vollaufzählung ----------
@pytest.mark.parametrize("S,H", [(2, 2), (2, 3), (3, 2), (3, 3)])
def test_matches_brute_force_on_tiny_instances(S, H):
    for seed in range(40):
        inst = generate_instance(S, H, 1.0, 6, seed)
        assert solve_exact(inst).optimum == brute_force_optimum(S, H, list(inst.events)), (S, H, seed)


def test_brute_force_itself_on_hand_case():
    ev = _events(("A", 0), ("A", 1), ("A", 2), ("D", 0), ("D", 1), ("D", 2))
    assert brute_force_optimum(2, 3, ev) == 1
    assert brute_force_optimum(3, 3, ev) == 0


# ---------- Referenzwerte aus der Messreihe (alter, geprüfter Code) ----------
# ((Stapel, Höhe, Füllgrad, Container, Seed), Optimum, Bestfit mit wahren Abfahrten)
PINS = [
    ((4, 4, 1.0, 30, 4), 4, 7), ((4, 4, 1.0, 30, 7), 2, 12), ((4, 4, 1.0, 30, 8), 2, 7),
    ((4, 3, 1.0, 24, 7), 2, 7), ((4, 3, 1.0, 24, 16), 2, 2), ((4, 3, 1.0, 24, 23), 2, 2),
    ((3, 4, 1.0, 20, 4), 3, 7), ((3, 4, 1.0, 20, 8), 2, 4), ((3, 4, 1.0, 20, 10), 4, 5),
    ((3, 3, 1.0, 14, 3), 1, 4),
]


@pytest.mark.parametrize("params,optimum,upper", PINS)
def test_reproduces_measured_optima(params, optimum, upper):
    inst = generate_instance(*params)
    r = solve_exact(inst, time_limit=60)
    assert r.proven and r.optimum == optimum == r.lower_bound
    assert r.upper_bound == upper == run_rule(inst, C.RULE_BESTFIT, 0.0).moves


# ---------- Eigenschaften ----------
@pytest.mark.parametrize("S,H,n", [(3, 3, 10), (4, 3, 12), (3, 4, 12)])
def test_optimum_is_a_lower_bound_for_every_rule(S, H, n):
    for seed in range(15):
        inst = generate_instance(S, H, 1.0, n, seed)
        opt = solve_exact(inst).optimum
        for key in C.RULE_KEYS:
            for sigma in (0.0, 0.5, 2.0):
                assert run_rule(inst, key, sigma).moves >= opt, (S, H, n, seed, key, sigma)


def test_result_is_consistent_when_proven():
    inst = generate_instance(4, 4, 1.0, 30, 7)
    r = solve_exact(inst, time_limit=60)
    assert isinstance(r, ExactResult) and r.proven and r.limit_reason is None
    assert r.lower_bound == r.optimum <= r.upper_bound
    assert r.calls > 0 and r.seconds >= 0


def test_is_deterministic():
    inst = generate_instance(4, 3, 1.0, 24, 7)
    a, b = solve_exact(inst, time_limit=60), solve_exact(inst, time_limit=60)
    assert (a.optimum, a.lower_bound, a.upper_bound, a.calls) == (b.optimum, b.lower_bound, b.upper_bound, b.calls)


def test_search_effort_regression():
    """Aufrufzahlen (deterministisch, nicht Zeit): schwere Instanz aus der Messreihe.
    Vor der Machbarkeitssuche mit Kindersortierung: 2 337 327 Aufrufe, danach rund 614 000."""
    r = solve_exact(generate_instance(4, 4, 1.0, 30, 4), time_limit=60)
    assert r.optimum == 4
    assert r.calls < 1_000_000


def test_stack_blockers_hand_cases():
    d = {0: 1, 1: 5, 2: 3, 3: 9, 4: 2}
    assert stack_blockers((), d) == 0
    assert stack_blockers((0, 4, 2), d) == 2                     # 4 (d=2) und 2 (d=3) über 0 (d=1)
    assert stack_blockers((3, 1, 2, 0), d) == 0                  # streng fallend: nichts blockiert
    assert stack_blockers((0, 1, 2), d) == 2


def test_reaches_blocks_that_plain_memoisation_could_not():
    # 4x4 mit 18 Containern: die Suche ohne Schranke war nach über 5 Minuten (30 Instanzen) nicht fertig
    for seed in range(4):
        r = solve_exact(generate_instance(4, 4, 1.0, 18, seed), time_limit=20)
        assert r.proven and r.seconds < 10


# ---------- Limits: Intervall statt unbewiesenem Optimum ----------
def test_call_limit_gives_interval_never_a_fake_optimum():
    inst = generate_instance(4, 4, 1.0, 30, 7)                     # Optimum 2, Bestfit 12
    r = solve_exact(inst, max_calls=1)
    assert not r.proven and r.optimum is None
    assert r.limit_reason == "Rechenlimit"
    assert r.lower_bound == 0 and r.upper_bound == 12


def test_interval_always_contains_the_optimum_and_tightens_with_more_work():
    for params, optimum, upper in PINS[:6]:
        inst = generate_instance(*params)
        last_lower = 0
        for calls in (1, 30, 300, 3000, 30000, None):
            r = solve_exact(inst, max_calls=calls, time_limit=60)
            assert r.lower_bound <= optimum <= r.upper_bound == upper, (params, calls)
            assert r.lower_bound >= last_lower                    # wird nie schlechter
            last_lower = r.lower_bound
            if r.proven:
                assert r.optimum == optimum
        assert r.proven                                           # ohne Limit gelöst


def test_time_limit_gives_interval(monkeypatch):
    monkeypatch.setattr(stk_exact, "CHECK_EVERY", 1)               # Zeit bei jedem Aufruf prüfen
    inst = generate_instance(4, 4, 1.0, 30, 7)
    r = solve_exact(inst, time_limit=0)
    assert not r.proven and r.limit_reason == "Zeitlimit"
    assert r.lower_bound <= 2 <= r.upper_bound


def test_large_instance_hits_limit_without_recursion_error():
    inst = generate_instance(6, 5, 0.8, 300, 0)                    # 600 Ereignisse, weit über Pythons Standard-Rekursionsgrenze
    before = sys.getrecursionlimit()
    r = solve_exact(inst, max_calls=20000)
    assert not r.proven and r.lower_bound <= r.upper_bound
    assert sys.getrecursionlimit() == before                       # Grenze wieder zurückgesetzt


def test_invalid_time_limit_raises():
    with pytest.raises(ValueError):
        solve_exact(generate_instance(3, 3, 1.0, 5, 0), time_limit=-1)
