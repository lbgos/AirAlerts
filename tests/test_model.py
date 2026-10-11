"""Overconfidence punishment: penalty score and the conservative calibrator."""

import numpy as np

from ua_alert_forecast.model import Conservative, WaveGateModel, penalty, points, wilson


def test_penalty_weights_confident_wrong_forecasts():
    plain = penalty(np.array([0.0]), np.array([0.6]))  # wrong but not confident
    assert np.isclose(plain, -np.log(0.4))
    assert np.isclose(penalty(np.array([0.0]), np.array([0.9])), 10 * -np.log(0.1))  # said 90%, did not happen


def test_wilson_bound_widens_with_few_cases():
    lo_small, _ = wilson(np.array([9.0]), np.array([10.0]))
    lo_big, _ = wilson(np.array([900.0]), np.array([1000.0]))
    assert lo_small < lo_big < 0.9


def test_conservative_never_claims_more_than_observed():
    rng = np.random.default_rng(0)
    raw = rng.uniform(0, 1, 20000)
    y = (rng.uniform(0, 1, 20000) < 0.3 + 0.4 * raw).astype(float)  # true rate never above 0.7 or below 0.3
    cal = Conservative.fit(raw, y)
    p = cal(np.linspace(0, 1, 101))
    assert np.all(np.diff(p) >= -1e-12)  # monotone
    assert p.max() <= 0.71 and p.min() >= 0.29  # no forecast more extreme than what actually happened


def test_points_reward_confident_right_and_punish_confident_wrong():
    clim = np.array([0.3])
    right_sure, right_unsure = points(np.array([1]), np.array([0.9]), clim), points(np.array([1]), np.array([0.7]), clim)
    wrong_sure = points(np.array([0]), np.array([0.9]), clim)
    assert right_sure > 3 * right_unsure > 0  # x3 reward on top of the bigger gain
    assert wrong_sure < -10 * abs(points(np.array([0]), np.array([0.7]), clim))


def test_wave_gate_is_the_product_of_its_stages():
    """The two-stage model's promise: P(siren in h) = P(wave within 3h) * P(siren in h | wave within 3h)."""
    import pandas as pd

    class Stub:
        def __init__(self, p):
            self.p = p

        def predict(self, rows):
            return np.full(len(rows), self.p)

    rows = pd.DataFrame({"a": [1, 2, 3]})
    gate, hazard = Stub(0.6), Stub(0.5)
    model = WaveGateModel("15m", [], gate, hazard)
    out = model.predict(rows)
    assert np.allclose(out, 0.3)
