"""Panel-Test über Streamlits AppTest: rendert alle vier Regel-Panels in einem Skript (fängt doppelte Widget-IDs)."""

from streamlit.testing.v1 import AppTest


def _script():
    import streamlit as st

    import stk_constants as C
    from stk_evaluation import compare_rules
    from stk_scenario import generate_instance
    from stk_ui_panel import render_rule_panel

    inst = generate_instance(6, 5, 0.8, 60, 1)
    outcomes = compare_rules(inst, 0.25)
    tabs = st.tabs([o.label for o in outcomes])
    for tab, o in zip(tabs, outcomes):
        with tab:
            render_rule_panel(f"rule_{o.key}", o, outcomes)


def _color(metric):
    enum = metric.proto.DESCRIPTOR.fields_by_name["color"].enum_type
    return enum.values_by_number[metric.proto.color].name


def _run():
    at = AppTest.from_function(_script)
    at.run(timeout=60)
    return at


def test_all_four_panels_render_without_exception():
    at = _run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.tabs) == 4
    assert len(at.metric) == 16                                    # 4 Kennzahlen je Panel


def test_metrics_values_and_delta_direction():
    at = _run()
    labels = [m.label for m in at.metric]
    assert labels == ["Umstapelungen", "pro Container", "Abholungen mit Umstapelung", "Höchster Stapel"] * 4
    moves = [m for m in at.metric if m.label == "Umstapelungen"]
    # Reihenfolge der Tabs: Zufällig, Niedrigster Stapel (Alltagsregel), Bestfit, Unsicherheits-bewusst; feste Werte aus der Messreihe
    assert [m.value for m in moves] == ["20", "6", "5", "2"]
    assert [m.delta for m in moves] == ["+14", "", "-1", "-4"]
    # delta_color="inverse": MEHR Umstapelungen als die Alltagsregel = rot, weniger = grün
    assert [_color(m) for m in moves] == ["RED", "GRAY", "GREEN", "GREEN"]
    per = [m for m in at.metric if m.label == "pro Container"]
    assert per[1].value == "0.10" and per[2].value == "0.08"             # 6/60 und 5/60
    assert per[2].delta == "-0.02" and _color(per[2]) == "GREEN"
    share = [m for m in at.metric if m.label == "Abholungen mit Umstapelung"]
    assert all(m.value.endswith(" %") for m in share)


def test_baseline_panel_has_no_delta_and_texts_are_shown():
    at = _run()
    baseline_moves = [m for m in at.metric if m.label == "Umstapelungen"][1]
    assert not baseline_moves.delta
    md = " ".join(m.value for m in at.markdown)
    assert "Alltagsregel" in md and "vertraut der Schätzung" in md
    assert any("dieselbe Regel (Bestfit)" in c.value for c in at.caption)
