import pytest

import stk_constants as C
from stk_scenario import capacity_for, estimate_departures, generate_instance


def _occupancy_profile(instance):
    occ, peak, profile = 0, 0, []
    for kind, _ in instance.events:
        occ += 1 if kind == "A" else -1
        profile.append(occ)
        peak = max(peak, occ)
    return profile, peak


def test_pinned_small_instance():
    # Referenz aus der Messreihe (hafen-planung/messreihe_stapel): make_instance(3, 3, 1.0, 6, 5)
    i = generate_instance(3, 3, 1.0, 6, 5)
    assert i.events == (("A", 0), ("D", 0), ("A", 1), ("D", 1), ("A", 2), ("D", 2), ("A", 3), ("D", 3),
                        ("A", 4), ("A", 5), ("D", 5), ("D", 4))
    assert i.departure == {0: 1, 1: 3, 2: 5, 3: 7, 5: 10, 4: 11}
    assert i.capacity == 6


def test_is_deterministic_and_seed_dependent():
    a = generate_instance(5, 4, 0.8, 50, 11)
    b = generate_instance(5, 4, 0.8, 50, 11)
    c = generate_instance(5, 4, 0.8, 50, 12)
    assert a == b
    assert a.events != c.events


@pytest.mark.parametrize("S,H,fill,n,seed", [(2, 1, 1.0, 5, 0), (3, 3, 1.0, 20, 1), (6, 5, 0.4, 60, 2),
                                             (8, 6, 1.0, 100, 3), (4, 3, 0.05, 30, 4)])
def test_events_are_well_formed(S, H, fill, n, seed):
    i = generate_instance(S, H, fill, n, seed)
    assert len(i.events) == 2 * n
    assert sorted(i.arrival) == sorted(i.departure) == list(range(n))
    for c in range(n):
        assert i.events[i.arrival[c]] == ("A", c)
        assert i.events[i.departure[c]] == ("D", c)
        assert i.arrival[c] < i.departure[c]
    assert i.mean_dwell >= 1
    profile, peak = _occupancy_profile(i)
    assert min(profile) >= 0 and profile[-1] == 0
    assert peak <= i.capacity                       # Belegungsgrenze eingehalten
    assert peak <= (S - 1) * H + 1                  # Grenze, unter der das Umstapeln immer Platz findet


def test_capacity_scales_with_fill():
    assert capacity_for(6, 5, 1.0) == 25
    assert capacity_for(6, 5, 0.8) == 20
    assert capacity_for(6, 5, 0.6) == 15
    assert capacity_for(3, 3, 0.01) == 1            # nie unter 1


def test_low_fill_keeps_block_nearly_empty():
    i = generate_instance(6, 5, 0.1, 100, 0)
    _, peak = _occupancy_profile(i)
    assert peak <= i.capacity == 2


@pytest.mark.parametrize("kwargs", [dict(n_stacks=1), dict(max_height=0), dict(fill=0), dict(fill=1.01), dict(n_containers=0)])
def test_invalid_parameters_raise(kwargs):
    params = dict(n_stacks=4, max_height=3, fill=0.8, n_containers=10, seed=0)
    params.update(kwargs)
    with pytest.raises(ValueError):
        generate_instance(**params)


# ---------- Schätzung ----------
def test_zero_sigma_estimates_equal_truth():
    i = generate_instance(5, 4, 0.8, 40, 3)
    assert estimate_departures(i, 0.0) == {c: float(d) for c, d in i.departure.items()}


def test_sigma_only_stretches_the_same_errors():
    i = generate_instance(5, 4, 0.8, 40, 3)
    e1, e2 = estimate_departures(i, 0.5), estimate_departures(i, 1.0)
    for c, d in i.departure.items():
        assert (e2[c] - d) == pytest.approx(2 * (e1[c] - d))


def test_noise_seed_is_an_independent_stream():
    i = generate_instance(5, 4, 0.8, 40, 3)
    default = estimate_departures(i, 0.5)
    assert estimate_departures(i, 0.5) == default                       # reproduzierbar
    assert estimate_departures(i, 0.5, noise_seed=99) != default        # anderer Strom, andere Fehler
    assert generate_instance(5, 4, 0.8, 40, 3) == i                     # Ereignisse unberührt
    assert C.NOISE_SEED_MULTIPLIER * 3 + C.NOISE_SEED_OFFSET == 44
    assert estimate_departures(i, 0.5, noise_seed=44) == default        # explizit = Standard


def test_negative_sigma_raises():
    with pytest.raises(ValueError):
        estimate_departures(generate_instance(3, 3, 1.0, 5, 0), -0.1)
