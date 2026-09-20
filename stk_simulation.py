"""Ablauf im Block: Einlagern nach Regel, Abholen in wahrer Reihenfolge, Umstapeln der Blocker.

Beim Abholen werden nur die Container über dem Ziel umgestapelt (restricted relocation), jeder Hub zählt
als eine Umstapelung. Ziel-Stapel eines Blockers: stk_rules.RELOCATION_RULE (für alle Regeln dieselbe).
"""

from dataclasses import dataclass

import stk_constants as C
from stk_rules import RELOCATION_RULE, make_rule
from stk_scenario import estimate_departures


@dataclass(frozen=True)
class Step:
    """Zustand nach einem Ereignis (nur wenn record=True)."""
    kind: str               # "A" Ankunft, "D" Abholung
    container: int
    stack: int              # Ankunft: gewählter Stapel; Abholung: Stapel, aus dem abgeholt wurde
    moved: tuple            # Abholung: umgestapelte Container (oberster zuerst), sonst ()
    stacks: tuple           # Blockzustand, Tupel von Tupeln (unten nach oben)
    moves_so_far: int


@dataclass(frozen=True)
class Result:
    moves: int
    retrievals: int
    retrievals_with_move: int
    max_stack_height: int
    cumulative: tuple       # kumulierte Umstapelungen nach jedem Ereignis
    steps: tuple            # leer, wenn nicht aufgezeichnet

    @property
    def moves_per_container(self):
        return self.moves / self.retrievals if self.retrievals else 0.0

    @property
    def share_retrievals_with_move(self):
        return self.retrievals_with_move / self.retrievals if self.retrievals else 0.0


def run(instance, estimates, place_rule, reloc_rule=RELOCATION_RULE, record=False):
    """Simuliert die Ereignisfolge der Instanz mit der Einlagerungsregel place_rule."""
    H = instance.max_height
    stacks = [[] for _ in range(instance.n_stacks)]
    where = {}
    moves = retrievals = with_move = max_height_seen = 0
    cumulative, steps = [], []

    for kind, c in instance.events:
        moved = []
        if kind == "A":
            i = place_rule(stacks, H, estimates[c], estimates)
            stacks[i].append(c)
            where[c] = i
            max_height_seen = max(max_height_seen, len(stacks[i]))
            stack_used = i
        else:
            x = where[c]
            s = stacks[x]
            while s[-1] != c:
                b = s.pop()
                j = reloc_rule(stacks, H, estimates[b], estimates, exclude=x)
                stacks[j].append(b)
                where[b] = j
                moved.append(b)
                max_height_seen = max(max_height_seen, len(stacks[j]))
            s.pop()
            del where[c]
            retrievals += 1
            if moved:
                with_move += 1
            moves += len(moved)
            stack_used = x
        cumulative.append(moves)
        if record:
            steps.append(Step(kind, c, stack_used, tuple(moved), tuple(tuple(s) for s in stacks), moves))

    return Result(moves, retrievals, with_move, max_height_seen, tuple(cumulative), tuple(steps))


def run_rule(instance, rule_key, sigma, noise_seed=None, record=False):
    """Bequemer Einstieg: schätzt die Abfahrten mit Fehler sigma (Bruchteil der mittleren Standzeit)
    und simuliert die Regel. Zufalls-Regel: Zufallsstrom aus dem Ereignis-Seed."""
    est = estimate_departures(instance, sigma, noise_seed)
    rule = make_rule(rule_key, seed=instance.seed, sigma_abs=sigma * instance.mean_dwell)
    return run(instance, est, rule, record=record)
