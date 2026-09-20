"""Plotly-Figuren der Stapelplanung-Demo: Blockansicht, σ-Kurve, kumulierte Umstapelungen, Regelbalken.

Alle Achsen sind fest (fixedrange): Touch-Geräte scrollen die Seite statt im Diagramm zu zoomen/schieben.
Plotly wird erst in den Funktionen importiert, damit die reine Rechnung ohne Plotly testbar bleibt.
"""

import stk_constants as C

# Legende unten im Container (oben rutscht sie in manchen Fenstern ins Diagramm)
LEGEND_BOTTOM = dict(orientation="h", yref="container", yanchor="bottom", y=0.0, x=0)

STACK_W = 1.0          # Breite eines Stapels (Achseneinheiten)
STACK_GAP = 0.3        # Abstand zwischen Stapeln
BOX_PAD = 0.06         # Innenabstand eines Containers im Stapel
BOX_H = 0.88           # Höhe eines Containers (Stapelebene = 1.0)


def _lock_axes(fig):
    # fixedrange: verhindert Pinch-Zoom/Ziehen, damit Touch-Geräte die Seite scrollen (Hover bleibt).
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _blend(f):
    a, b = C.BLOCK_COLOR_SOON, C.BLOCK_COLOR_LATE
    return tuple(int(round(a[i] + f * (b[i] - a[i]))) for i in range(3))


# ---------------------------------------------------------------------------------------------------
# Blockansicht
# ---------------------------------------------------------------------------------------------------
def block_title(label, moves_so_far):
    """Zweizeiliger Titel: in halbbreiten Spalten ist eine Zeile zu lang und wird abgeschnitten."""
    return f"<b>{label}</b><br><sub>Umstapelungen bisher: {moves_so_far}</sub>"


def state_at(instance, result, event_index):
    """Blockzustand nach `event_index` Ereignissen (0 = leer vor dem ersten Ereignis).

    Gibt (stacks, moved, arrived, event) zurück; result muss mit record=True gerechnet sein."""
    if event_index == 0:
        return tuple(() for _ in range(instance.n_stacks)), (), None, None
    step = result.steps[event_index - 1]
    arrived = step.container if step.kind == "A" else None
    return step.stacks, step.moved, arrived, step


def block_figure(stacks, max_height, departure, title, moved=(), arrived=None, estimates=None):
    """Block als Stapel von Containern. Farbe/Zahl = wahre Abfahrtsreihenfolge unter den anwesenden Containern."""
    import plotly.graph_objects as go

    present = [c for s in stacks for c in s]
    rank = {c: r for r, c in enumerate(sorted(present, key=lambda k: departure[k]))}
    span = max(1, len(present) - 1)

    fig = go.Figure()
    n = len(stacks)
    for i in range(n):
        x0 = i * (STACK_W + STACK_GAP)
        fig.add_shape(type="rect", x0=x0, x1=x0 + STACK_W, y0=0, y1=max_height, layer="below",
                      fillcolor=C.BLOCK_STACK_BG, line=dict(color=C.BLOCK_STACK_LINE, width=1))

    xs, ys, texts, colors, hovers = [], [], [], [], []
    for i, s in enumerate(stacks):
        x0 = i * (STACK_W + STACK_GAP)
        for t, c in enumerate(s):
            f = rank[c] / span
            r, g, b = _blend(f)
            border = C.MOVED_COLOR if c in moved else (C.ARRIVED_COLOR if c == arrived else None)
            fig.add_shape(
                type="rect", x0=x0 + BOX_PAD, x1=x0 + STACK_W - BOX_PAD, y0=t + (1 - BOX_H) / 2, y1=t + (1 - BOX_H) / 2 + BOX_H,
                fillcolor=f"rgb({r},{g},{b})", layer="below",       # unter der Text-Spur, sonst verdecken die Formen die Zahlen
                line=dict(color=border, width=3) if border else dict(width=0),
            )
            xs.append(x0 + STACK_W / 2)
            ys.append(t + 0.5)
            texts.append(str(rank[c] + 1))
            colors.append("white" if f < 0.5 else "#1c2430")
            state = "gerade umgestapelt" if c in moved else ("gerade angekommen" if c == arrived else "")
            hover = (f"<b>Container {c}</b>{' · ' + state if state else ''}<br>Stapel {i + 1}, Ebene {t + 1}"
                     f"<br>Abfahrt in Reihenfolge: {rank[c] + 1} von {len(present)}")
            if estimates is not None:
                hover += f"<br>geschätzte Abfahrt: Schritt {estimates[c]:.1f} · wahre: Schritt {departure[c]}"
            hovers.append(hover)

    # eine Text-Spur trägt Zahlen UND Hover (Linien-Hover wäre punktbasiert; Zentren sind die Punkte)
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="text", text=texts, textfont=dict(size=12, color=colors), hovertext=hovers,
        hoverinfo="text", showlegend=False,
    ))
    total_w = n * STACK_W + (n - 1) * STACK_GAP
    fig.update_layout(
        title=dict(text=title, font=dict(size=14), x=0.02),
        template="plotly_white", showlegend=False,
        height=C.BLOCK_FIGURE_BASE_PX + 14 + max_height * C.BLOCK_FIGURE_TIER_PX,
        margin=dict(l=8, r=8, t=58, b=8),
    )
    fig.update_xaxes(range=[-0.1, total_w + 0.1], visible=False)
    fig.update_yaxes(range=[-0.05, max_height + 0.05], visible=False)
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# σ-Kurve (Kernabschnitt)
# ---------------------------------------------------------------------------------------------------
def sigma_curve_figure(sweep, sigma_current, tipping):
    """Umstapelungen pro Container je Regel über den Schätzfehler, Band = ± 1 Standardfehler."""
    import plotly.graph_objects as go

    fig = go.Figure()
    xs = [s * 100 for s in sweep.sigmas]
    for key in C.RULE_KEYS:
        color = C.RULE_COLORS[key]
        means = [sweep.mean(key, i) for i in range(len(xs))]
        sems = [sweep.sem(key, i) for i in range(len(xs))]
        upper = [m + e for m, e in zip(means, sems)]
        lower = [m - e for m, e in zip(means, sems)]
        fig.add_trace(go.Scatter(x=xs + xs[::-1], y=upper + lower[::-1], fill="toself", fillcolor=color, opacity=0.15,
                                 line=dict(width=0), hoverinfo="skip", showlegend=False, name=f"{C.RULE_LABELS[key]} (Band)"))
        fig.add_trace(go.Scatter(
            x=xs, y=means, mode="lines+markers", name=C.RULE_LABELS[key], line=dict(color=color, width=2.5),
            marker=dict(size=6),
            hovertemplate=f"<b>{C.RULE_LABELS[key]}</b><br>Schätzfehler %{{x:.0f}} %<br>%{{y:.3f}} Umstapelungen pro Container<extra></extra>",
        ))

    fig.add_vline(x=sigma_current * 100, line=dict(color=C.MARKER_LINE_COLOR, width=2, dash="dot"),
                  annotation_text="eingestellt", annotation_position="top", annotation_font=dict(size=11))
    if tipping is not None and 0 < tipping <= sweep.sigmas[-1]:
        fig.add_vline(x=tipping * 100, line=dict(color="#c0392b", width=2, dash="dash"),
                      annotation_text=f"Kipppunkt ≈ {tipping * 100:.0f} %", annotation_position="bottom right",
                      annotation_font=dict(size=12, color="#c0392b"))
    fig.update_layout(
        template="plotly_white", height=C.CHART_HEIGHT + 40, legend=LEGEND_BOTTOM, margin=dict(t=30, b=110),
        xaxis_title="Schätzfehler σ (% der mittleren Standzeit)", yaxis_title="Umstapelungen pro Container",
        hovermode="closest",
    )
    fig.update_yaxes(rangemode="tozero")
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Kumulierte Umstapelungen über die Ereignisse
# ---------------------------------------------------------------------------------------------------
def cumulative_figure(outcomes, focus_key, cursor=None):
    """Kumulierte Umstapelungen der Regel `focus_key` gegen die Alltagsregel über die Ereignisse."""
    import plotly.graph_objects as go

    by_key = {o.key: o for o in outcomes}
    keys = [C.BASELINE_RULE] if focus_key == C.BASELINE_RULE else [C.BASELINE_RULE, focus_key]
    fig = go.Figure()
    for key in keys:
        o = by_key[key]
        cum = (0,) + tuple(o.result.cumulative)
        fig.add_trace(go.Scatter(
            x=list(range(len(cum))), y=list(cum), mode="lines", name=o.label, line=dict(color=C.RULE_COLORS[key], width=2.5, shape="hv"),
            hovertemplate=f"<b>{o.label}</b><br>nach Ereignis %{{x}}: %{{y}} Umstapelungen<extra></extra>",
        ))
    if cursor is not None:
        fig.add_vline(x=cursor, line=dict(color=C.MARKER_LINE_COLOR, width=2, dash="dot"))
    fig.update_layout(
        template="plotly_white", height=C.CHART_HEIGHT - 80, legend=LEGEND_BOTTOM, margin=dict(t=20, b=90),
        xaxis_title="Ereignis (Ankunft oder Abholung)", yaxis_title="Umstapelungen kumuliert", hovermode="x unified",
    )
    fig.update_yaxes(rangemode="tozero")
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Regelbalken (mit Optimum)
# ---------------------------------------------------------------------------------------------------
def rule_bar_figure(outcomes, exact=None):
    """Umstapelungen gesamt je Regel; optional das Optimum mit Hellsehen als Linie (bewiesen) oder Band (Intervall)."""
    import plotly.graph_objects as go

    fig = go.Figure(go.Bar(
        x=[o.label for o in outcomes], y=[o.moves for o in outcomes],
        marker_color=[C.RULE_COLORS[o.key] for o in outcomes], text=[o.moves for o in outcomes], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y} Umstapelungen<extra></extra>", showlegend=False,
    ))
    top = max([o.moves for o in outcomes] + [exact.upper_bound if exact is not None else 0])
    if exact is not None:
        if exact.proven:
            fig.add_hline(y=exact.optimum, line=dict(color=C.OPTIMUM_COLOR, width=2, dash="dash"),
                          annotation_text=f"Optimum mit Hellsehen: {exact.optimum}", annotation_position="top left",
                          annotation_font=dict(color=C.OPTIMUM_COLOR))
        else:
            fig.add_hrect(y0=exact.lower_bound, y1=exact.upper_bound, fillcolor=C.OPTIMUM_COLOR, opacity=0.15, line_width=0,
                          annotation_text=f"Optimum liegt zwischen {exact.lower_bound} und {exact.upper_bound} (nicht bewiesen)",
                          annotation_position="top left", annotation_font=dict(color=C.OPTIMUM_COLOR))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT - 60, margin=dict(t=30, b=40),
                      yaxis_title="Umstapelungen gesamt")
    fig.update_yaxes(range=[0, top * 1.2 + 1])
    return _lock_axes(fig)
