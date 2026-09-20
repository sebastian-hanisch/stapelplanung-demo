"""Wiederverwendbares Panel zur Darstellung einer Regel im Methodenvergleich (je Regel ein Tab)."""

import streamlit as st

import stk_constants as C
from stk_visualization import cumulative_figure


def render_rule_panel(prefix, outcome, outcomes):
    """Beschreibung, Kennzahlen und kumulierte Umstapelkurve einer Regel.

    Deltas lesen sich immer als "diese Regel minus Alltagsregel" (delta_color="inverse": weniger ist besser).
    prefix macht die Widget-Schlüssel eindeutig."""
    baseline = next(o for o in outcomes if o.key == C.BASELINE_RULE)
    r, b = outcome.result, baseline.result
    is_baseline = outcome.key == baseline.key

    st.markdown(C.RULE_DESCRIPTIONS[outcome.key])
    st.caption("Beim Abholen entscheidet für alle Regeln dieselbe Regel (Bestfit), wohin ein Blocker umgestapelt wird. "
               "So misst der Vergleich nur die Einlagerungsentscheidung.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Umstapelungen", f"{r.moves}", delta=None if is_baseline else f"{r.moves - b.moves:+d}", delta_color="inverse",
              help="Anzahl unproduktiver Kranhübe über den ganzen Ablauf.")
    m2.metric("pro Container", f"{r.moves_per_container:.2f}",
              delta=None if is_baseline else f"{r.moves_per_container - b.moves_per_container:+.2f}", delta_color="inverse")
    m3.metric("Abholungen mit Umstapelung", f"{r.share_retrievals_with_move * 100:.0f} %",
              help="Anteil der Abholungen, bei denen mindestens ein Container im Weg lag.")
    m4.metric("Höchster Stapel", f"{r.max_stack_height}")

    st.plotly_chart(cumulative_figure(outcomes, outcome.key), width="stretch", key=f"{prefix}_cumulative_chart")
