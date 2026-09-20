"""Optimum mit Hellsehen: exakte Suche (IDA*-artig) nach der kleinstmöglichen Zahl an Umstapelungen.

Das Optimum kennt die wahren Abfahrten UND die gesamte Ankunftsfolge und darf Einlagerungs- und
Umstapelziele frei wählen. Es ist damit eine untere Schranke für jede Online-Regel und nicht erreichbar.

Verfahren
  * Zustand = (Ereignisindex, sortierte Stapel). Stapel werden sortiert, weil ihre Reihenfolge im Block
    keine Rolle spielt (Symmetriebruch).
  * Untere Schranke h: Anzahl Container, die über einem früher abfahrenden liegen. Jeder von ihnen muss
    mindestens einmal umgestapelt werden (er kann nicht vor dem tieferen abfahren), h ist also zulässig.
    Sie wird je Stapel gemerkt, weil dieselben Stapel in sehr vielen Zuständen vorkommen.
  * Iterative Vertiefung über das Umstapel-Budget von 0 bis zur oberen Schranke (Bestfit mit wahren
    Abfahrten, eine gültige Lösung). Je Budget wird nur gefragt "gibt es eine Fortsetzung mit höchstens
    so vielen Umstapelungen?" (Machbarkeitssuche). Sie bricht beim ersten Fund ab; deshalb werden
    die Kinder eines Knotens so sortiert, dass die vielversprechendsten zuerst kommen (Bestfit-Reihenfolge:
    nichts Früheres blockieren, möglichst eng, sonst kleinster Schaden). Das ändert nur die Reihenfolge,
    nie das Ergebnis. Teilbäume mit h > Budget fallen weg; bewiesene Machbarkeit und Unmachbarkeit
    werden je Zustand und Budget gemerkt (Transpositionstabelle).
  * Das erste machbare Budget ist das Optimum, denn alle kleineren sind bewiesen unmachbar.
  * Läuft die Suche in ein Limit (Zeit oder Aufrufe), ist die Antwort ein INTERVALL: untere Schranke =
    das zuletzt begonnene Budget (alle kleineren sind bewiesen gescheitert), obere Schranke = Bestfit.
    Ein unbewiesener Wert wird nie als Optimum ausgegeben.
"""

import sys
import time
from dataclasses import dataclass

from stk_rules import bestfit
from stk_simulation import run

INF = float("inf")
DEFAULT_TIME_LIMIT = 10.0     # Sekunden
CHECK_EVERY = 256             # Aufrufe zwischen zwei Zeitprüfungen


class _LimitReached(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ExactResult:
    optimum: int | None        # None: nicht bewiesen (Limit erreicht), dann gilt das Intervall
    lower_bound: int           # bewiesen: Optimum >= lower_bound
    upper_bound: int           # gültige Lösung (Bestfit mit wahren Abfahrten): Optimum <= upper_bound
    calls: int
    seconds: float
    limit_reason: str | None   # "Zeitlimit", "Rechenlimit" oder None

    @property
    def proven(self):
        return self.optimum is not None


def stack_blockers(stack, departure):
    """Container in einem Stapel (unten nach oben), die über einem früher abfahrenden liegen."""
    total, earliest_below = 0, INF
    for c in stack:
        d = departure[c]
        if d > earliest_below:
            total += 1
        else:
            earliest_below = d
    return total


def blocking_lower_bound(stacks, departure):
    """Anzahl Container, die über einem früher abfahrenden Container im selben Stapel liegen."""
    return sum(stack_blockers(s, departure) for s in stacks)


class _Search:
    def __init__(self, instance, deadline, max_calls):
        self.events = instance.events
        self.n_events = len(instance.events)
        self.departure = instance.departure
        self.max_height = instance.max_height
        self.deadline = deadline
        self.max_calls = max_calls
        self.calls = 0
        self.feasible_at = {}     # Zustand -> kleinstes Budget, für das Machbarkeit bewiesen ist
        self.infeasible_at = {}   # Zustand -> größtes Budget, das als unmachbar bewiesen ist
        self.blockers_of = {}     # Stapel -> Anzahl Blocker (gemerkt)

    def _candidates(self, stacks, exclude, d_own):
        """Zulässige Ziel-Stapel in Bestfit-Reihenfolge (identische Stapel nur einmal)."""
        dep, H = self.departure, self.max_height
        cand, seen = [], set()
        for k, s in enumerate(stacks):
            if k == exclude or len(s) >= H or s in seen:
                continue
            seen.add(s)
            top = dep[s[-1]] if s else INF
            cand.append(((0, top) if top >= d_own else (1, -top), k))
        cand.sort()
        return [k for _, k in cand]

    def feasible(self, i, stacks, budget):
        """Gibt es ab Ereignis i eine Fortsetzung mit höchstens `budget` Umstapelungen?"""
        self.calls += 1
        if self.max_calls is not None and self.calls > self.max_calls:
            raise _LimitReached("Rechenlimit")
        if self.deadline is not None and self.calls % CHECK_EVERY == 0 and time.monotonic() >= self.deadline:
            raise _LimitReached("Zeitlimit")
        if i == self.n_events:
            return True

        key = (i, stacks)
        known_ok = self.feasible_at.get(key)
        if known_ok is not None and known_ok <= budget:
            return True
        known_bad = self.infeasible_at.get(key, -1)
        if known_bad >= budget:
            return False

        blockers_of, dep = self.blockers_of, self.departure
        h = 0
        for s in stacks:
            b = blockers_of.get(s)
            if b is None:
                b = blockers_of[s] = stack_blockers(s, dep)
            h += b
        if h > budget:
            self.infeasible_at[key] = max(known_bad, h - 1)     # jedes Budget unter h ist unmachbar
            return False

        kind, c = self.events[i]
        found = False
        if kind == "A":
            for k in self._candidates(stacks, None, dep[c]):
                nxt = list(stacks)
                nxt[k] = stacks[k] + (c,)
                if self.feasible(i + 1, tuple(sorted(nxt)), budget):
                    found = True
                    break
        else:
            x = next(k for k, s in enumerate(stacks) if c in s)
            s = stacks[x]
            pos = s.index(c)
            blockers = s[pos + 1:][::-1]                        # oberster zuerst
            if len(blockers) <= budget:
                base = list(stacks)
                base[x] = s[:pos + 1]                           # Blocker abgehoben, Ziel liegt noch obenauf
                found = self._relocate(i, x, s[:pos], blockers, 0, tuple(base), budget)

        if found:
            if known_ok is None or budget < known_ok:
                self.feasible_at[key] = budget
            return True
        self.infeasible_at[key] = max(known_bad, budget)
        return False

    def _relocate(self, i, x, rest_of_x, blockers, idx, cur, budget):
        """Verteilt die Blocker (oberster zuerst) auf die anderen Stapel; True, sobald eine Verteilung reicht."""
        if idx == len(blockers):
            final = list(cur)
            final[x] = rest_of_x                                # Ziel verlässt den Block
            return self.feasible(i + 1, tuple(sorted(final)), budget - len(blockers))
        b = blockers[idx]
        for k in self._candidates(cur, x, self.departure[b]):
            nxt = list(cur)
            nxt[k] = cur[k] + (b,)
            if self._relocate(i, x, rest_of_x, blockers, idx + 1, tuple(nxt), budget):
                return True
        return False


def solve_exact(instance, time_limit=DEFAULT_TIME_LIMIT, max_calls=None):
    """Optimum mit Hellsehen für die Instanz (wahre Abfahrten, bekannte Ankunftsfolge).

    time_limit  Sekunden (None = unbegrenzt), max_calls  Obergrenze der Suchaufrufe (None = unbegrenzt,
    dient vor allem deterministischen Tests). Gibt ExactResult zurück, bei Limit mit Intervall statt Optimum.
    """
    if time_limit is not None and time_limit < 0:
        raise ValueError("time_limit darf nicht negativ sein.")
    started = time.monotonic()
    deadline = None if time_limit is None else started + time_limit

    upper = run(instance, {c: float(d) for c, d in instance.departure.items()}, bestfit).moves
    search = _Search(instance, deadline, max_calls)
    start = tuple(() for _ in range(instance.n_stacks))

    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, instance.n_events * (instance.max_height + 2) + 500))
    try:
        for budget in range(0, upper + 1):
            # alle kleineren Budgets sind bewiesen unmachbar
            try:
                ok = search.feasible(0, start, budget)
            except _LimitReached as limit:
                return ExactResult(None, budget, upper, search.calls, time.monotonic() - started, limit.reason)
            if ok:
                return ExactResult(budget, budget, upper, search.calls, time.monotonic() - started, None)
    finally:
        sys.setrecursionlimit(old_limit)
    raise RuntimeError("Keine Lösung unter der oberen Schranke gefunden - das darf nicht passieren.")
