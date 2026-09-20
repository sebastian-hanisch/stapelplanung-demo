"""Einlagerungsregeln und die gemeinsame Umstapel-Regel.

Jede Regel bekommt den aktuellen Blockzustand und entscheidet, in welchen Stapel ein Container kommt:

    rule(stacks, max_height, e_own, est, exclude=None) -> Stapelindex

stacks   Liste von Listen (Container-IDs, unten nach oben)
e_own    geschätzte Abfahrt des zu platzierenden Containers
est      Schätzung aller Container: id -> geschätzte Abfahrt
exclude  Stapel, der nicht in Frage kommt (beim Umstapeln der Stapel, aus dem der Blocker stammt)
"""

import math
import random

import stk_constants as C

INF = float("inf")


def _candidates(stacks, max_height, exclude):
    cand = [i for i, s in enumerate(stacks) if i != exclude and len(s) < max_height]
    if not cand:
        raise ValueError("Kein Stapel mit freiem Platz: Belegung liegt über der zulässigen Grenze.")
    return cand


def bestfit(stacks, max_height, e_own, est, exclude=None):
    """Nichts Früheres blockieren, möglichst eng: Stapel mit dem kleinsten obersten ê >= eigenem ê
    (leere Stapel zählen als unendlich, werden also zuletzt genommen). Blockiert jeder Kandidat, der
    Stapel mit dem größten obersten ê (kleinster Schaden)."""
    cand = _candidates(stacks, max_height, exclude)
    good = bad = None
    for i in cand:
        s = stacks[i]
        top = est[s[-1]] if s else INF
        if top >= e_own:
            if good is None or top < good[0]:
                good = (top, i)
        elif bad is None or top > bad[0]:
            bad = (top, i)
    return (good or bad)[1]


def niedrigster_stapel(stacks, max_height, e_own, est, exclude=None):
    """Ausgleich: Stapel mit den wenigsten Containern (bei Gleichstand der kleinste Index). Ignoriert die Schätzung."""
    cand = _candidates(stacks, max_height, exclude)
    return min(cand, key=lambda i: (len(stacks[i]), i))


def make_random_rule(seed):
    rng = random.Random(seed)

    def zufaellig(stacks, max_height, e_own, est, exclude=None):
        return rng.choice(_candidates(stacks, max_height, exclude))
    return zufaellig


def make_aware_rule(sigma_abs):
    """Unsicherheits-bewusst: minimiert die Wahrscheinlichkeit, einen früher abfahrenden Container zu
    blockieren, P = Phi((ê_eigen - ê_oben) / (sigma * sqrt 2)). Leere Stapel haben P = 0. sigma_abs ist der
    absolute Schätzfehler in Ereignisschritten."""
    sig = max(sigma_abs, 1e-9)

    def unsicherheitsbewusst(stacks, max_height, e_own, est, exclude=None):
        best = None
        for i in _candidates(stacks, max_height, exclude):
            s = stacks[i]
            if s:
                top = est[s[-1]]
                p = 0.5 * (1 + math.erf((e_own - top) / (sig * math.sqrt(2))))
            else:
                top, p = INF, 0.0
            key = (round(p, C.AWARE_P_DECIMALS), top if p < C.AWARE_TIGHTFIT_BELOW_P else len(s), i)
            if best is None or key < best[0]:
                best = (key, i)
        return best[1]
    return unsicherheitsbewusst


# Für ALLE Regeln entscheidet dieselbe Regel, wohin ein Blocker beim Abholen umgestapelt wird.
# So misst der Vergleich nur die Einlagerungsentscheidung.
RELOCATION_RULE = bestfit


def make_rule(key, seed=0, sigma_abs=0.0):
    if key == C.RULE_RANDOM:
        return make_random_rule(seed)
    if key == C.RULE_LOWEST:
        return niedrigster_stapel
    if key == C.RULE_BESTFIT:
        return bestfit
    if key == C.RULE_AWARE:
        return make_aware_rule(sigma_abs)
    raise ValueError(f"Unbekannte Regel: {key!r}")
