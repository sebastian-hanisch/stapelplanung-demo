"""Unabhängige Orakel (anderer Rechenweg als der Demo-Code), klein und schnell.

* Simulation + Regeln: eigener Simulator; die Blockierwahrscheinlichkeit der unsicherheits-bewussten Regel kommt
  aus scipy.stats.norm.cdf statt aus math.erf. Das fängt den Fund der Orakel-Prüfung: Phi(d / sigma) statt
  Phi(d / (sigma * sqrt 2)) (der Schätzfehler der Differenz zweier Schätzungen ist sigma * sqrt 2).
* Exakt-Löser: kürzester Weg (Dijkstra) im Zustandsgraphen mit EINZELNEN Umstapelungen als Kanten der Kosten 1.
"""

import heapq
import math
import random

import pytest

import stk_constants as C
from stk_exact import solve_exact
from stk_scenario import estimate_departures, generate_instance
from stk_simulation import run_rule

INF = float("inf")


def _bestfit(stacks, H, e, est, excl=None):
    ok = bad = None
    for i, s in enumerate(stacks):
        if i == excl or len(s) >= H:
            continue
        top = est[s[-1]] if s else INF
        if top >= e:
            ok = (top, i) if ok is None or top < ok[0] else ok
        else:
            bad = (top, i) if bad is None or top > bad[0] else bad
    return (ok or bad)[1]


def _rule(key, inst, sigma):
    norm = pytest.importorskip("scipy.stats").norm
    sig = max(sigma * inst.mean_dwell, 1e-9)
    rng = random.Random(inst.seed)

    def rule(stacks, H, e, est):
        cand = [i for i, s in enumerate(stacks) if len(s) < H]
        if key == C.RULE_RANDOM:
            return rng.choice(cand)
        if key == C.RULE_LOWEST:
            return min(cand, key=lambda i: (len(stacks[i]), i))
        if key == C.RULE_BESTFIT:
            return _bestfit(stacks, H, e, est)
        rows = []
        for i in cand:
            s = stacks[i]
            top, p = (est[s[-1]], float(norm.cdf((e - est[s[-1]]) / (sig * math.sqrt(2))))) if s else (INF, 0.0)
            rows.append(((round(p, 2), top if p < 0.3 else len(s), i), i))
        return min(rows)[1]
    return rule


def _simulate(inst, est, rule):
    H = inst.max_height
    stacks = [[] for _ in range(inst.n_stacks)]
    moves = 0
    for kind, c in inst.events:
        if kind == "A":
            stacks[rule(stacks, H, est[c], est)].append(c)
        else:
            x = next(k for k, s in enumerate(stacks) if c in s)
            pos = stacks[x].index(c)
            above = stacks[x][pos + 1:][::-1]
            stacks[x] = stacks[x][:pos + 1]
            for b in above:
                stacks[_bestfit(stacks, H, est[b], est, x)].append(b)
                moves += 1
            stacks[x].pop()
    return moves


def test_rules_and_simulation_match_independent_simulator():
    rng = random.Random(11)
    for _ in range(25):
        inst = generate_instance(rng.randint(2, 7), rng.randint(2, 5), rng.choice([0.5, 0.8, 1.0]),
                                 rng.randint(10, 60), rng.randint(0, 999))
        sigma = rng.choice([0.0, 0.25, 0.5, 1.0, 2.0])
        est = estimate_departures(inst, sigma)
        for key in C.RULE_KEYS:
            assert run_rule(inst, key, sigma).moves == _simulate(inst, est, _rule(key, inst, sigma)), (key, sigma, inst.seed)


def test_aware_rule_probability_uses_difference_sigma_times_sqrt2():
    # Handfall: eigenes ê = 0, sigma = 2, oberste ê der drei Stapel 8 (Höhe 2), -1 (Höhe 3), 6 (Höhe 1).
    # P = Phi((ê_eigen - ê_oben) / (sigma * sqrt 2)): Phi(-2.83) = 0.0023 -> 0.00, Phi(0.35) = 0.64, Phi(-2.12) = 0.0169 -> 0.02.
    # Stapel 0 hat das kleinste gerundete P und gewinnt. Mit dem fehlerhaften Phi(d / sigma) wären es 0.00003 und 0.0013,
    # beide gerundet 0.00, und die enge Passung (oberstes ê = 6) würde Stapel 2 wählen.
    from stk_rules import make_aware_rule
    est = {0: 5.0, 1: 8.0, 2: 5.0, 3: 5.0, 4: -1.0, 5: 5.0}
    stacks = [[0, 1], [2, 3, 4], [5]]
    est[5] = 6.0
    assert make_aware_rule(2.0)(stacks, 4, 0.0, est) == 0


# ---------- Exakt-Löser gegen kürzesten Weg im Zustandsgraphen ----------
def _dijkstra_optimum(S, H, events):
    n = len(events)
    start = (0, tuple(() for _ in range(S)))
    dist, pq, cnt = {start: 0}, [(0, 0, start)], 0
    while pq:
        d, _, st = heapq.heappop(pq)
        if dist.get(st, INF) < d:
            continue
        i, stacks = st
        if i == n:
            return d
        kind, c = events[i]
        succ = []
        if kind == "A":
            for k in range(S):
                if len(stacks[k]) < H:
                    ns = list(stacks)
                    ns[k] = stacks[k] + (c,)
                    succ.append((0, (i + 1, tuple(sorted(ns)))))
        else:
            x = next(k for k, s in enumerate(stacks) if c in s)
            if stacks[x][-1] == c:
                ns = list(stacks)
                ns[x] = stacks[x][:-1]
                succ.append((0, (i + 1, tuple(sorted(ns)))))
            else:
                b = stacks[x][-1]
                for k in range(S):
                    if k != x and len(stacks[k]) < H:
                        ns = list(stacks)
                        ns[x] = stacks[x][:-1]
                        ns[k] = stacks[k] + (b,)
                        succ.append((1, (i, tuple(sorted(ns)))))
        for w, ns in succ:
            if d + w < dist.get(ns, INF):
                dist[ns] = d + w
                cnt += 1
                heapq.heappush(pq, (d + w, cnt, ns))
    return INF


def test_dijkstra_oracle_hand_cases():
    ev = [("A", 0), ("A", 1), ("A", 2), ("D", 0), ("D", 1), ("D", 2)]
    assert _dijkstra_optimum(2, 3, ev) == 1 and _dijkstra_optimum(3, 3, ev) == 0


def test_exact_matches_shortest_path_on_random_instances():
    rng = random.Random(5)
    for _ in range(40):
        S, H = rng.choice([2, 3, 4]), rng.choice([2, 3])
        inst = generate_instance(S, H, rng.choice([0.5, 1.0]), rng.randint(4, 8), rng.randint(0, 9999))
        res = solve_exact(inst, time_limit=20)
        assert res.proven and res.optimum == _dijkstra_optimum(S, H, list(inst.events)), (S, H, inst.seed)
