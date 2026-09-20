"""Regler-Spezifikation, Permalink, Presets und Zufalls-Seed-Button (Standardmuster aus dem OR-Demo-Portfolio,
siehe z.B. berth_presets.py)."""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import stk_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None
    step: Optional[int] = None


SETTING_SPECS = {
    "n_stacks_slider": SettingSpec("ns", int, C.N_STACKS_DEFAULT, *C.N_STACKS_RANGE, 1),
    "max_height_slider": SettingSpec("mh", int, C.MAX_HEIGHT_DEFAULT, *C.MAX_HEIGHT_RANGE, 1),
    "fill_slider": SettingSpec("fp", int, C.FILL_PCT_DEFAULT, *C.FILL_PCT_RANGE, C.FILL_PCT_STEP),
    "n_containers_slider": SettingSpec("nc", int, C.N_CONTAINERS_DEFAULT, *C.N_CONTAINERS_RANGE, C.N_CONTAINERS_STEP),
    "sigma_slider": SettingSpec("sg", int, C.SIGMA_PCT_DEFAULT, *C.SIGMA_PCT_RANGE, C.SIGMA_PCT_STEP),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE, 1),
}

PRESET_STATE_KEYS = {
    "n_stacks": "n_stacks_slider", "max_height": "max_height_slider", "fill_pct": "fill_slider",
    "n_containers": "n_containers_slider", "sigma_pct": "sigma_slider", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, auf den Bereich begrenzen, auf die Schrittweite runden.
    None, wenn er sich nicht auswerten lässt."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    if spec.step and spec.step > 1 and spec.lo is not None:
        value = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = min(spec.hi, value)
    return value


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = parse_setting(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """values: dict state_key -> aktueller Wert (aus den Widgets, nicht aus session_state, damit dieselbe Änderung,
    die gerade gerendert wurde, auch sofort in der Adresszeile landet)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(int(value))
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(C.SEED_RANGE[0], C.SEED_RANGE[1])
