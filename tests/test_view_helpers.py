"""Hilfen der Blickansicht: Vergleichspartner, Startpunkt, Beschreibung eines Ereignisses."""

import stk_constants as C
from stk_evaluation import RuleOutcome, comparison_partner, compare_rules, describe_step, suggested_event
from stk_scenario import generate_instance
from stk_simulation import Result, Step, run_rule


def _outcomes(**moves):
    def res(m):
        return Result(m, 10, min(10, m), 3, tuple(range(m)), ())
    return tuple(RuleOutcome(k, C.RULE_LABELS[k], res(moves[k])) for k in C.RULE_KEYS)


def test_comparison_partner_is_best_non_baseline_rule():
    assert comparison_partner(_outcomes(zufaellig=9, niedrigster_stapel=5, bestfit=3, unsicherheitsbewusst=4)).key == C.RULE_BESTFIT
    # Alltagsregel ist die beste: Partner ist trotzdem die beste Alternative
    assert comparison_partner(_outcomes(zufaellig=9, niedrigster_stapel=1, bestfit=3, unsicherheitsbewusst=4)).key == C.RULE_BESTFIT
    # Gleichstand unter den Alternativen: Bestfit vor Aware vor Zufällig
    assert comparison_partner(_outcomes(zufaellig=3, niedrigster_stapel=5, bestfit=3, unsicherheitsbewusst=3)).key == C.RULE_BESTFIT
    assert comparison_partner(_outcomes(zufaellig=3, niedrigster_stapel=5, bestfit=4, unsicherheitsbewusst=3)).key == C.RULE_AWARE


def test_suggested_event_picks_relocation_at_highest_occupancy():
    inst = generate_instance(6, 5, 0.8, 120, 3)
    res = compare_rules(inst, 0.25)[1].result                          # Niedrigster Stapel
    k = suggested_event(res)
    step = res.steps[k - 1]
    assert step.kind == "D" and step.moved
    occupancy = sum(len(s) for s in step.stacks)
    for other in res.steps:
        if other.kind == "D" and other.moved:
            assert sum(len(s) for s in other.stacks) <= occupancy     # keine Abholung mit Umstapelung ist voller
    assert k == 175                                                   # fester Wert (Startpunkt auch im Mockup der Planseite)


def test_suggested_event_falls_back_to_fullest_moment_without_relocations():
    inst = generate_instance(6, 5, 0.6, 40, 2)
    res = run_rule(inst, C.RULE_BESTFIT, 0.0, record=True)
    assert res.moves == 0
    k = suggested_event(res)
    occupancy = [sum(len(s) for s in st.stacks) for st in res.steps]
    assert occupancy[k - 1] == max(occupancy) and 1 <= k <= inst.n_events


def test_describe_step_texts():
    n = 20
    assert describe_step(None, 0, n) == "Ereignis 0 von 20: Der Block ist noch leer."
    arrive = Step("A", 7, 2, (), ((), (), (7,)), 0)
    assert describe_step(arrive, 3, n) == "Ereignis 3 von 20: Container 7 kommt an und wird auf Stapel 3 gelegt."
    clean = Step("D", 4, 0, (), ((),), 0)
    assert describe_step(clean, 9, n) == "Ereignis 9 von 20: Container 4 wird aus Stapel 1 abgeholt, ohne Umstapelung."
    one = Step("D", 4, 1, (9,), ((),), 1)
    assert "muss 1 Container umgestapelt" in describe_step(one, 9, n)
    many = Step("D", 4, 1, (9, 8, 6), ((),), 3)
    assert "müssen 3 Container umgestapelt" in describe_step(many, 9, n)
