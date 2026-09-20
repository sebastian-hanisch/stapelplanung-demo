import pytest

import stk_constants as C
from stk_presets import PRESET_STATE_KEYS, SETTING_SPECS, SettingSpec, bounds, parse_setting


def _aligned(spec, value):
    return spec.lo <= value <= spec.hi and (value - spec.lo) % spec.step == 0


def test_setting_specs_match_constants_and_defaults_are_valid():
    assert bounds("n_stacks_slider") == C.N_STACKS_RANGE and bounds("max_height_slider") == C.MAX_HEIGHT_RANGE
    assert bounds("fill_slider") == C.FILL_PCT_RANGE and bounds("n_containers_slider") == C.N_CONTAINERS_RANGE
    assert bounds("sigma_slider") == C.SIGMA_PCT_RANGE and bounds("seed_input") == C.SEED_RANGE
    for key, spec in SETTING_SPECS.items():
        assert spec.lo < spec.hi, key                                 # nie min == max (Slider-Absturz)
        assert _aligned(spec, spec.default), key


def test_url_params_are_unique():
    params = [s.url_param for s in SETTING_SPECS.values()]
    assert len(params) == len(set(params))


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_is_inside_the_slider_bounds_and_on_the_step_grid(name):
    """Das Preset 'Kleiner Block' setzte zuerst 30 Container bei einer Untergrenze von 40: Streamlit-Exception."""
    preset = C.PRESETS[name]
    assert set(preset) == set(PRESET_STATE_KEYS)
    for field, state_key in PRESET_STATE_KEYS.items():
        assert _aligned(SETTING_SPECS[state_key], preset[field]), (name, field, preset[field])


def test_exact_preset_exists_and_is_small():
    p = C.PRESETS[C.EXACT_PRESET]
    assert p["n_stacks"] * p["max_height"] <= 16 and p["n_containers"] <= 30


# ---------- parse_setting ----------
SPEC = SETTING_SPECS["fill_slider"]                # 40..100, Schritt 5


@pytest.mark.parametrize("raw,expected", [("80", 80), ("83", 85), ("82", 80), ("999", 100), ("-5", 40), ("40", 40), ("100", 100)])
def test_parse_setting_clamps_and_snaps_to_step(raw, expected):
    assert parse_setting(SPEC, raw) == expected


@pytest.mark.parametrize("raw", ["abc", "", "nan", "1e3", None, "8.5"])
def test_parse_setting_rejects_unparsable_values(raw):
    assert parse_setting(SPEC, raw) is None


def test_parse_setting_step_one_and_float_caster():
    assert parse_setting(SETTING_SPECS["n_stacks_slider"], "5") == 5
    assert parse_setting(SETTING_SPECS["n_stacks_slider"], "50") == 8
    fspec = SettingSpec("x", float, 0.5, 0.0, 1.0)
    assert parse_setting(fspec, "0.25") == 0.25 and parse_setting(fspec, "2") == 1.0
    assert parse_setting(fspec, "nan") is None and parse_setting(fspec, "inf") is None      # nicht endliche Zahlen
