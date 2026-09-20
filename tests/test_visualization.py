import itertools
import json

import pytest

import stk_constants as C
from stk_evaluation import compare_rules, sigma_sweep, tipping_point
from stk_exact import ExactResult
from stk_scenario import estimate_departures, generate_instance
from stk_visualization import (STACK_GAP, STACK_W, block_figure, cumulative_figure, rule_bar_figure, sigma_curve_figure,
                               state_at)


def _all_figures():
    inst = generate_instance(6, 5, 0.8, 60, 1)
    outs = compare_rules(inst, 0.25)
    res = outs[2].result
    k = max(range(len(res.steps)), key=lambda i: sum(len(s) for s in res.steps[i].stacks)) + 1
    stacks, moved, arrived, _ = state_at(inst, res, k)
    sw = sigma_sweep(6, 5, 0.8, 40, 0.25, n_instances=6)
    return [
        block_figure(stacks, inst.max_height, inst.departure, "Bestfit", moved, arrived, estimate_departures(inst, 0.25)),
        sigma_curve_figure(sw, 0.25, tipping_point(sw)),
        cumulative_figure(outs, C.RULE_BESTFIT, cursor=k),
        rule_bar_figure(outs, ExactResult(2, 2, 9, 10, 0.1, None)),
    ]


# ---------- gemeinsame Konventionen ----------
@pytest.mark.parametrize("fig", _all_figures())
def test_every_figure_locks_axes_is_json_and_uses_white_template(fig):
    assert fig.layout.xaxis.fixedrange is True and fig.layout.yaxis.fixedrange is True   # Touch-Scrollen
    json.loads(fig.to_json())
    assert fig.layout.template.layout.plot_bgcolor == "white"                         # plotly_white wie im Portfolio


# ---------- Blockansicht ----------
def _boxes(fig):
    """Container-Rechtecke (alles außer den Stapel-Hintergründen)."""
    return [s for s in fig.layout.shapes if s.fillcolor != C.BLOCK_STACK_BG]


def _stack_rects(fig):
    return [s for s in fig.layout.shapes if s.fillcolor == C.BLOCK_STACK_BG]


def _overlap(a, b):
    ox = min(a.x1, b.x1) - max(a.x0, b.x0)
    oy = min(a.y1, b.y1) - max(a.y0, b.y0)
    return ox > 1e-9 and oy > 1e-9


def _block(seed=1, event_fraction=0.7, n=60, fill=0.8, S=6, H=5, sigma=0.25, rule=C.RULE_LOWEST):
    inst = generate_instance(S, H, fill, n, seed)
    outs = compare_rules(inst, sigma)
    res = next(o for o in outs if o.key == rule).result
    k = max(1, int(len(res.steps) * event_fraction))
    stacks, moved, arrived, step = state_at(inst, res, k)
    est = estimate_departures(inst, sigma)
    return inst, stacks, moved, arrived, step, block_figure(stacks, H, inst.departure, "t", moved, arrived, est)


def test_state_at_boundaries_and_kinds():
    inst = generate_instance(4, 3, 0.8, 20, 2)
    res = compare_rules(inst, 0.0)[2].result
    stacks, moved, arrived, step = state_at(inst, res, 0)
    assert stacks == ((),) * 4 and moved == () and arrived is None and step is None
    for k in range(1, inst.n_events + 1):
        stacks, moved, arrived, step = state_at(inst, res, k)
        assert stacks == res.steps[k - 1].stacks
        assert (arrived == step.container) == (step.kind == "A")
        assert moved == step.moved
    assert state_at(inst, res, inst.n_events)[0] == ((),) * 4


@pytest.mark.parametrize("seed,frac,rule", [(1, 0.7, C.RULE_LOWEST), (2, 0.5, C.RULE_BESTFIT), (3, 0.9, C.RULE_RANDOM),
                                             (4, 0.3, C.RULE_AWARE), (5, 0.6, C.RULE_LOWEST)])
def test_block_geometry_boxes_fit_do_not_overlap_and_labels_sit_inside(seed, frac, rule):
    inst, stacks, moved, arrived, step, fig = _block(seed, frac, rule=rule)
    present = [c for s in stacks for c in s]
    boxes, stack_rects = _boxes(fig), _stack_rects(fig)
    assert len(stack_rects) == inst.n_stacks and len(boxes) == len(present)
    for a, b in itertools.combinations(boxes, 2):
        assert not _overlap(a, b), "Container überlappen"
    for a, b in itertools.combinations(stack_rects, 2):
        assert not _overlap(a, b), "Stapel überlappen"
    for bx in boxes:                                   # jeder Container liegt vollständig in genau einem Stapel
        inside = [s for s in stack_rects if s.x0 <= bx.x0 and bx.x1 <= s.x1 and s.y0 <= bx.y0 and bx.y1 <= s.y1]
        assert len(inside) == 1
    text = fig.data[0]
    assert len(text.x) == len(present)
    for x, y in zip(text.x, text.y):                   # jede Zahl liegt im Mittelpunkt eines Containers
        assert sum(1 for b in boxes if b.x0 < x < b.x1 and b.y0 < y < b.y1) == 1
    assert all(s.layer == "below" for s in fig.layout.shapes)     # sonst verdecken Formen die Zahlen


def test_block_labels_are_the_departure_ranks_and_colors_follow_them():
    inst, stacks, moved, arrived, step, fig = _block(2, 0.7)
    present = [c for s in stacks for c in s]
    text = fig.data[0]
    assert sorted(int(t) for t in text.text) == list(range(1, len(present) + 1))      # Ränge 1..m genau einmal
    rank_of = {}
    for i, s in enumerate(stacks):
        for t, c in enumerate(s):
            rank_of[c] = int([tx for x, y, tx in zip(text.x, text.y, text.text)
                              if abs(x - (i * (STACK_W + STACK_GAP) + STACK_W / 2)) < 1e-9 and abs(y - (t + 0.5)) < 1e-9][0])
    expected = {c: r + 1 for r, c in enumerate(sorted(present, key=lambda k: inst.departure[k]))}
    assert rank_of == expected                                                       # Zahl = Rang der WAHREN Abfahrt
    # Farbe wird mit dem Rang heller: Rot-Anteil steigt monoton
    reds = []
    for rk in range(1, len(present) + 1):
        i = list(text.text).index(str(rk))
        x, y = text.x[i], text.y[i]
        box = next(b for b in _boxes(fig) if b.x0 < x < b.x1 and b.y0 < y < b.y1)
        reds.append(int(box.fillcolor[4:-1].split(",")[0]))
    assert reds == sorted(reds)


def test_block_marks_moved_and_arrived_containers():
    for seed in range(1, 8):
        inst, stacks, moved, arrived, step, fig = _block(seed, 0.6, rule=C.RULE_RANDOM)
        orange = [s for s in _boxes(fig) if s.line.color == C.MOVED_COLOR]
        green = [s for s in _boxes(fig) if s.line.color == C.ARRIVED_COLOR]
        assert len(orange) == len(moved)
        assert len(green) == (1 if arrived is not None else 0)
    # eine Abholung mit Umstapelung und eine Ankunft gezielt suchen
    inst = generate_instance(6, 5, 0.8, 80, 3)
    res = compare_rules(inst, 0.25)[0].result
    k_move = next(i for i, s in enumerate(res.steps) if s.kind == "D" and len(s.moved) >= 2) + 1
    stacks, moved, arrived, _ = state_at(inst, res, k_move)
    fig = block_figure(stacks, 5, inst.departure, "t", moved, arrived)
    assert len([s for s in _boxes(fig) if s.line.color == C.MOVED_COLOR]) == len(moved) >= 2
    k_arr = next(i for i, s in enumerate(res.steps) if s.kind == "A") + 1
    stacks, moved, arrived, _ = state_at(inst, res, k_arr)
    fig = block_figure(stacks, 5, inst.departure, "t", moved, arrived)
    assert len([s for s in _boxes(fig) if s.line.color == C.ARRIVED_COLOR]) == 1


def test_block_hover_names_container_stack_and_estimate():
    inst, stacks, moved, arrived, step, fig = _block(2, 0.7)
    hovers = fig.data[0].hovertext
    assert all("Container" in h and "Stapel" in h and "geschätzte Abfahrt" in h for h in hovers)
    inst2 = generate_instance(4, 3, 0.8, 20, 2)
    res = compare_rules(inst2, 0.0)[1].result
    stacks, moved, arrived, _ = state_at(inst2, res, 10)
    without = block_figure(stacks, 3, inst2.departure, "t")
    assert all("geschätzte Abfahrt" not in h for h in without.data[0].hovertext)


def test_block_empty_and_full_and_tiny():
    inst = generate_instance(3, 2, 1.0, 10, 0)
    empty = block_figure(state_at(inst, compare_rules(inst, 0.0)[1].result, 0)[0], 2, inst.departure, "leer")
    assert len(_stack_rects(empty)) == 3 and len(_boxes(empty)) == 0 and list(empty.data[0].x) == []
    full = block_figure(((0, 1), (2, 3)), 2, {0: 3, 1: 2, 2: 1, 3: 0}, "voll")
    assert len(_boxes(full)) == 4 and sorted(full.data[0].text) == ["1", "2", "3", "4"]
    single = block_figure(((5,), ()), 2, {5: 7}, "einzeln")                    # ein Container: Rang 1, keine Division durch 0
    assert single.data[0].text == ("1",) and len(_boxes(single)) == 1


def test_block_axes_range_covers_all_stacks_and_height():
    fig = _block(1, 0.7, S=8, H=6)[5]
    total_w = 8 * STACK_W + 7 * STACK_GAP
    assert fig.layout.xaxis.range[0] < 0 and fig.layout.xaxis.range[1] > total_w
    assert fig.layout.yaxis.range[1] > 6
    assert max(s.x1 for s in _stack_rects(fig)) <= fig.layout.xaxis.range[1]


# ---------- σ-Kurve ----------
def test_sigma_curve_traces_values_and_marker_lines():
    sw = sigma_sweep(4, 3, 0.8, 30, 0.3, n_instances=5)
    tip = 0.8
    fig = sigma_curve_figure(sw, 0.3, tip)
    lines = {t.name: t for t in fig.data if t.mode == "lines+markers"}
    assert set(lines) == {C.RULE_LABELS[k] for k in C.RULE_KEYS}
    for key in C.RULE_KEYS:
        t = lines[C.RULE_LABELS[key]]
        assert list(t.x) == [s * 100 for s in sw.sigmas]
        assert list(t.y) == pytest.approx([sw.mean(key, i) for i in range(len(sw.sigmas))])
        assert t.line.color == C.RULE_COLORS[key]
    bands = [t for t in fig.data if t.fill == "toself"]
    assert len(bands) == 4 and all(len(b.x) == 2 * len(sw.sigmas) for b in bands)
    xs = sorted(s.x0 for s in fig.layout.shapes)
    assert xs == pytest.approx([30.0, 80.0])                                    # eingestellt und Kipppunkt (in %)
    assert fig.layout.legend.orientation == "h" and fig.layout.legend.yref == "container"


def test_sigma_curve_tipping_line_only_when_inside_the_range():
    sw = sigma_sweep(4, 3, 0.8, 30, 0.3, n_instances=3)
    assert len(sigma_curve_figure(sw, 0.3, None).layout.shapes) == 1
    assert len(sigma_curve_figure(sw, 0.3, 0.0).layout.shapes) == 1             # Kipppunkt 0: keine eigene Linie
    assert len(sigma_curve_figure(sw, 0.3, 5.0).layout.shapes) == 1             # außerhalb des Rasters
    assert len(sigma_curve_figure(sw, 0.3, 0.9).layout.shapes) == 2


def test_sigma_curve_band_is_mean_plus_minus_one_sem():
    sw = sigma_sweep(4, 3, 0.8, 30, 0.5, n_instances=6)
    fig = sigma_curve_figure(sw, 0.5, None)
    band = next(t for t in fig.data if t.fill == "toself")           # erste Regel = Zufällig
    n = len(sw.sigmas)
    upper, lower = list(band.y[:n]), list(band.y[n:])[::-1]
    for i in range(n):
        m, e = sw.mean(C.RULE_KEYS[0], i), sw.sem(C.RULE_KEYS[0], i)
        assert upper[i] == pytest.approx(m + e) and lower[i] == pytest.approx(m - e)


# ---------- kumulierte Kurve ----------
def test_cumulative_uses_baseline_and_focus():
    inst = generate_instance(5, 4, 0.8, 40, 2)
    outs = compare_rules(inst, 0.5)
    fig = cumulative_figure(outs, C.RULE_BESTFIT, cursor=25)
    assert [t.name for t in fig.data] == [C.RULE_LABELS[C.BASELINE_RULE], C.RULE_LABELS[C.RULE_BESTFIT]]
    for t, key in zip(fig.data, (C.BASELINE_RULE, C.RULE_BESTFIT)):
        o = next(x for x in outs if x.key == key)
        assert list(t.y) == [0] + list(o.result.cumulative) and list(t.x) == list(range(inst.n_events + 1))
        assert t.line.color == C.RULE_COLORS[key]
    assert [s.x0 for s in fig.layout.shapes] == [25]
    assert len(cumulative_figure(outs, C.BASELINE_RULE).data) == 1           # Alltagsregel: nur eine Kurve
    assert len(cumulative_figure(outs, C.RULE_BESTFIT).layout.shapes) == 0   # ohne Cursor keine Linie


def test_cumulative_ends_at_total_moves():
    inst = generate_instance(5, 4, 0.8, 40, 2)
    outs = compare_rules(inst, 0.5)
    for o in outs:
        assert cumulative_figure(outs, o.key).data[-1].y[-1] == o.moves


# ---------- Balken ----------
def test_bar_values_colors_and_optimum_line():
    inst = generate_instance(4, 4, 1.0, 30, 7)
    outs = compare_rules(inst, 0.25)
    fig = rule_bar_figure(outs, ExactResult(2, 2, 12, 100, 0.1, None))
    assert list(fig.data[0].y) == [o.moves for o in outs] and list(fig.data[0].x) == [o.label for o in outs]
    assert list(fig.data[0].marker.color) == [C.RULE_COLORS[o.key] for o in outs]
    line = fig.layout.shapes[0]
    assert line.type == "line" and line.y0 == line.y1 == 2 and line.line.color == C.OPTIMUM_COLOR
    assert "Optimum mit Hellsehen: 2" in fig.layout.annotations[0].text


def test_bar_interval_band_and_no_optimum():
    inst = generate_instance(4, 4, 1.0, 30, 7)
    outs = compare_rules(inst, 0.25)
    interval = rule_bar_figure(outs, ExactResult(None, 1, 17, 100, 10.0, "Zeitlimit"))
    band = interval.layout.shapes[0]
    assert band.type == "rect" and (band.y0, band.y1) == (1, 17)
    assert "nicht bewiesen" in interval.layout.annotations[0].text
    assert interval.layout.yaxis.range[1] > 17                                   # obere Schranke ist sichtbar
    assert len(rule_bar_figure(outs).layout.shapes) == 0


def test_bar_axis_range_always_shows_the_tallest_bar():
    outs = compare_rules(generate_instance(6, 5, 0.8, 60, 1), 0.25)
    fig = rule_bar_figure(outs)
    assert fig.layout.yaxis.range[0] == 0 and fig.layout.yaxis.range[1] > max(o.moves for o in outs)


def test_block_label_color_contrasts_with_box_color():
    """Weiße Zahl auf dunklen Kästen (Rang in der ersten Hälfte), dunkle Zahl auf hellen: sonst unlesbar."""
    inst, stacks, moved, arrived, step, fig = _block(2, 0.7)
    text = fig.data[0]
    m = len(text.text)
    for label, color in zip(text.text, text.textfont.color):
        f = (int(label) - 1) / max(1, m - 1)
        assert color == ("white" if f < 0.5 else "#1c2430")
    assert "white" in text.textfont.color and "#1c2430" in text.textfont.color        # beide Fälle kommen vor
