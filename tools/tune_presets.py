"""Preset-Abstimmung per Sweep: traegt die Aussage jedes Presets im MITTEL ueber viele Seeds, nicht nur beim gewaehlten?

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/tune_presets.py [population|candidates]

Grundsaetze (aus fruehreren Demos): Seeds nicht nach dem schoensten Einzelfall waehlen, sondern so, dass das Preset dem
Mittel entspricht; Ereignis-Seed UND Rausch-Seed pruefen (sonst kippt die Aussage bei anderem Rauschen)."""
import statistics as st
import sys

sys.path.insert(0, ".")
import stk_constants as C
from stk_scenario import generate_instance
from stk_simulation import run_rule

R = C.RULE_KEYS
SEEDS = range(200)
NOISE_SEEDS = range(20)


def moves(inst, rule, sigma, noise_seed=None):
    return run_rule(inst, rule, sigma, noise_seed).moves


def preset_instance(p, seed):
    return generate_instance(p["n_stacks"], p["max_height"], p["fill_pct"] / 100, p["n_containers"], seed)


def population(name):
    p = C.PRESETS[name]
    sigma = p["sigma_pct"] / 100
    rows = []
    for seed in SEEDS:
        inst = preset_instance(p, seed)
        rows.append({r: moves(inst, r, sigma) for r in R} | {"seed": seed, "sigma0_best": moves(inst, C.RULE_BESTFIT, 0.0),
                                                              "sigma0_low": moves(inst, C.RULE_LOWEST, 0.0)})
    return p, rows


def report(name):
    p, rows = population(name)
    n = len(rows)
    mean = {r: st.fmean(x[r] for x in rows) for r in R}
    print(f"\n### {name}  {p}")
    print("Mittel Umstapelungen:", {C.RULE_LABELS[r]: round(mean[r], 1) for r in R})
    share = lambda f: sum(1 for x in rows if f(x)) / n
    print(f"Anteil Seeds: bestfit < lowest {share(lambda x: x[C.RULE_BESTFIT] < x[C.RULE_LOWEST]):.0%} | lowest < bestfit {share(lambda x: x[C.RULE_LOWEST] < x[C.RULE_BESTFIT]):.0%} | "
          f"aware <= beide {share(lambda x: x[C.RULE_AWARE] <= min(x[C.RULE_LOWEST], x[C.RULE_BESTFIT])):.0%} | "
          f"zufaellig >= 2.5x bestfit {share(lambda x: x[C.RULE_BESTFIT] > 0 and x[C.RULE_RANDOM] >= 2.5 * x[C.RULE_BESTFIT]):.0%} | bestfit pro Container >= 0.4 {share(lambda x: x[C.RULE_BESTFIT] / p['n_containers'] >= 0.4):.0%}")
    ratio = [x[C.RULE_RANDOM] / x[C.RULE_BESTFIT] for x in rows if x[C.RULE_BESTFIT] > 0]
    if ratio:
        print(f"Verhaeltnis zufaellig/bestfit: Median {st.median(ratio):.1f}, 10%-Quantil {sorted(ratio)[len(ratio)//10]:.1f}, 90%-Quantil {sorted(ratio)[-len(ratio)//10]:.1f}")
    return p, rows


if __name__ == "__main__" and (len(sys.argv) == 1 or sys.argv[1] == "population"):
    for name in C.PRESETS:
        report(name)


# ---------------------------------------------------------------------------------------------------
# Kandidatensuche: ein Seed, der bei ALLEN Sigma-Presets typisch ist (nicht der schoenste Einzelfall)
# ---------------------------------------------------------------------------------------------------
def features(seed):
    p1, p2, p3, p4 = (C.PRESETS[n] for n in ("Perfekte Info", "Realistisch", "Kaum brauchbar", "Voller Block"))
    i80, i60, i100 = preset_instance(p1, seed), preset_instance(p3, seed), preset_instance(p4, seed)
    f = {}
    b0, l0, z0 = (moves(i80, r, 0.0) for r in (C.RULE_BESTFIT, C.RULE_LOWEST, C.RULE_RANDOM))
    f["r1"] = z0 / b0 if b0 else float("inf")                                        # Zufaellig / Bestfit bei sigma 0
    f["s1"] = 100 * (l0 - b0) / l0 if l0 else 0.0                                     # Ersparnis bei sigma 0
    b2, l2 = moves(i80, C.RULE_BESTFIT, 0.25), moves(i80, C.RULE_LOWEST, 0.25)
    f["s2"] = 100 * (l2 - b2) / l2 if l2 else 0.0                                     # Ersparnis bei sigma 25 %
    b3, l3, a3 = (moves(i60, r, 1.5) for r in (C.RULE_BESTFIT, C.RULE_LOWEST, C.RULE_AWARE))
    f["g3"] = 100 * (b3 - l3) / l3 if l3 else 0.0                                     # Bestfit schlechter als Ausgleich (in %)
    f["a3_le_low"] = a3 <= l3
    b4 = moves(i100, C.RULE_BESTFIT, 0.0)
    f["r4"] = b4 / b0 if b0 else float("inf")                                         # voller Block / Fuellgrad 80 %
    f["pc4"] = b4 / 120
    return f


def noise_robustness(seed):
    """Anteil der Rausch-Seeds, bei denen die Aussage von Preset 2 bzw. 3 haelt."""
    p2, p3 = C.PRESETS["Realistisch"], C.PRESETS["Kaum brauchbar"]
    i80, i60 = preset_instance(p2, seed), preset_instance(p3, seed)
    ok2 = sum(moves(i80, C.RULE_BESTFIT, 0.25, ns) < moves(i80, C.RULE_LOWEST, 0.25, ns) for ns in NOISE_SEEDS) / len(NOISE_SEEDS)
    ok3 = sum(moves(i60, C.RULE_LOWEST, 1.5, ns) < moves(i60, C.RULE_BESTFIT, 1.5, ns) for ns in NOISE_SEEDS) / len(NOISE_SEEDS)
    ok3a = sum(moves(i60, C.RULE_AWARE, 1.5, ns) <= moves(i60, C.RULE_LOWEST, 1.5, ns) for ns in NOISE_SEEDS) / len(NOISE_SEEDS)
    return ok2, ok3, ok3a


def candidates(top=8):
    feats = {s: features(s) for s in SEEDS}
    finite = lambda k: [f[k] for f in feats.values() if f[k] != float("inf")]
    med = {k: st.median(finite(k)) for k in ("r1", "s1", "s2", "g3", "r4", "pc4")}
    iqr = {k: (sorted(finite(k))[3 * len(finite(k)) // 4] - sorted(finite(k))[len(finite(k)) // 4]) or 1.0 for k in med}
    print("Median der Merkmale:", {k: round(v, 2) for k, v in med.items()})
    scored = []
    for s, f in feats.items():
        if not (f["s2"] > 0 and f["s2"] < f["s1"] and f["g3"] > 0 and f["a3_le_low"] and f["r1"] >= 2.5 and f["r4"] >= 1.5):
            continue
        dist = sum(abs(f[k] - med[k]) / iqr[k] for k in med)
        scored.append((dist, s))
    scored.sort()
    print(f"{len(scored)} von {len(feats)} Seeds erfuellen alle Nebenbedingungen; die typischsten:")
    for dist, s in scored[:top]:
        ok2, ok3, ok3a = noise_robustness(s)
        f = feats[s]
        print(f"  seed {s:3d} dist {dist:.2f} | r1 {f['r1']:.1f} s1 {f['s1']:.0f}% s2 {f['s2']:.0f}% g3 {f['g3']:+.0f}% r4 {f['r4']:.2f} pc4 {f['pc4']:.2f} | "
              f"Rauschen: P2 {ok2:.0%} P3 {ok3:.0%} P3aware<=low {ok3a:.0%}")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "candidates":
    candidates()


def robust_candidates(top=10):
    """Wie candidates(), aber ohne die schwache aware-Bedingung und mit Rauschstabilitaet als HARTER Bedingung (>= 90 %)."""
    feats = {s: features(s) for s in SEEDS}
    finite = lambda k: [f[k] for f in feats.values() if f[k] != float("inf")]
    med = {k: st.median(finite(k)) for k in ("r1", "s1", "s2", "g3", "r4", "pc4")}
    iqr = {k: (sorted(finite(k))[3 * len(finite(k)) // 4] - sorted(finite(k))[len(finite(k)) // 4]) or 1.0 for k in med}
    rows = []
    for s, f in feats.items():
        if not (f["s2"] > 0 and f["s2"] < f["s1"] and f["g3"] > 0 and f["r1"] >= 2.5 and f["r4"] >= 1.5):
            continue
        ok2, ok3, ok3a = noise_robustness(s)
        if ok2 >= 0.9 and ok3 >= 0.9:
            rows.append((sum(abs(f[k] - med[k]) / iqr[k] for k in med), s, f, ok2, ok3, ok3a))
    rows.sort(key=lambda r: r[0])
    print(f"{len(rows)} Seeds mit Rauschstabilitaet >= 90 % in Preset 2 und 3; die typischsten:")
    for dist, s, f, ok2, ok3, ok3a in rows[:top]:
        print(f"  seed {s:3d} dist {dist:.2f} | r1 {f['r1']:.1f} s1 {f['s1']:.0f}% s2 {f['s2']:.0f}% g3 {f['g3']:+.0f}% r4 {f['r4']:.2f} pc4 {f['pc4']:.2f} | P2 {ok2:.0%} P3 {ok3:.0%} aware<=low {ok3a:.0%}")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "robust":
    robust_candidates()


def small_block(n_seeds=100):
    """Preset 'Kleiner Block': Verhaeltnis Bestfit / Optimum und Loesungszeit ueber viele Seeds; typischen Seed nennen."""
    from stk_exact import solve_exact
    p = C.PRESETS["Kleiner Block"]
    rows = []
    for seed in range(n_seeds):
        inst = preset_instance(p, seed)
        r = solve_exact(inst, time_limit=8)
        if not r.proven:
            continue
        b, l = moves(inst, C.RULE_BESTFIT, 0.0), moves(inst, C.RULE_LOWEST, 0.0)
        rows.append(dict(seed=seed, opt=r.optimum, best=b, low=l, sec=r.seconds))
    print(f"{len(rows)} von {n_seeds} Seeds in 8 s exakt geloest; mittlere Zeit {st.fmean(x['sec'] for x in rows):.2f} s, max {max(x['sec'] for x in rows):.1f} s")
    print(f"Mittel: Optimum {st.fmean(x['opt'] for x in rows):.2f}, Bestfit {st.fmean(x['best'] for x in rows):.2f}, Ausgleich {st.fmean(x['low'] for x in rows):.2f}; "
          f"Verhaeltnis der Mittel Bestfit/Optimum {st.fmean(x['best'] for x in rows) / st.fmean(x['opt'] for x in rows):.2f}")
    good = [x for x in rows if x["opt"] >= 2 and x["best"] > x["opt"] and x["low"] > x["best"] and x["sec"] < 3]
    target = st.fmean(x["best"] for x in rows) / st.fmean(x["opt"] for x in rows)
    good.sort(key=lambda x: (abs(x["best"] / x["opt"] - target) + abs(x["opt"] - st.median(y["opt"] for y in rows)) * 0.2))
    print("typischste Seeds (Optimum >= 2, Bestfit > Optimum, Ausgleich > Bestfit, < 3 s):")
    for x in good[:8]:
        print(f"  seed {x['seed']:3d}  Optimum {x['opt']}  Bestfit {x['best']}  Ausgleich {x['low']}  Verhaeltnis {x['best'] / x['opt']:.1f}  {x['sec']:.2f} s")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "small":
    small_block()
