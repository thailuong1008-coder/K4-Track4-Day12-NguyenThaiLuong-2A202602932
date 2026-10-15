"""Step 2: scenarios. Metrics (TTC, required deceleration), mining braking events from the logs, and the physics
frontier that separates 'no planner could have avoided this' from 'this planner failed'."""
import numpy as np

from . import config as C


def ttc(gap, closing):
    """Time to collision [s] = gap / closing speed (inf when the gap is not closing)."""
    g = np.asanyarray(gap, dtype=float)
    c = np.asanyarray(closing, dtype=float)
    out = np.full(np.broadcast_shapes(g.shape, c.shape), np.inf, dtype=float)
    mask = c > 0
    np.divide(g, c, out=out, where=mask)
    if out.ndim == 0:
        return float(out)
    return out


def required_decel(gap, closing):
    """Deceleration [m/s^2] needed to remove the closing speed exactly at contact: closing^2 / (2 gap)."""
    g = np.asanyarray(gap, dtype=float)
    c = np.asanyarray(closing, dtype=float)
    out = np.zeros(np.broadcast_shapes(g.shape, c.shape), dtype=float)
    mask = (c > 0) & (g > 0)
    np.divide(c ** 2, 2.0 * g, out=out, where=mask)
    if out.ndim == 0:
        return float(out)
    return out


def unavoidable(gaps, dvs, t_react=0.0, b_max=C.B_MAX):
    """Boolean grid (len(dvs), len(gaps)): True where NO planner can avoid contact, even braking at b_max after the
    reaction delay: gap < dv * t_react + dv^2 / (2 b_max)  (lead keeps its speed)."""
    G, DV = np.meshgrid(gaps, dvs)
    needed_gap = DV * t_react + (DV ** 2) / (2.0 * b_max)
    return (DV > 0) & (G < needed_gap)


def mine_braking(logs, threshold=C.BRAKE_THRESHOLD, min_steps=5):
    """Find trajectories where the lead brakes: smoothed deceleration below `threshold` for at least `min_steps`
    consecutive steps (0.5 s). Returns a list of event dicts (one per trajectory, first event only)."""
    events = []
    for i in range(len(logs)):
        a = logs.a_lead[i, :logs.n[i]]
        is_braking = a < threshold
        start = None
        for t, b in enumerate(is_braking):
            if b:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if (t - start) >= min_steps:
                        onset_step = start
                        peak_decel = float(np.min(a[start:t]))
                        events.append({
                            "traj": int(i),
                            "onset_step": int(onset_step),
                            "peak_decel": float(peak_decel),
                            "gap_m": float(logs.gap[i, onset_step]),
                            "closing_m_s": float(logs.v_ego[i, onset_step] - logs.v_lead_s[i, onset_step]),
                            "ego_speed": float(logs.v_ego[i, onset_step]),
                        })
                        break
                    start = None
        else:
            if start is not None and (len(is_braking) - start) >= min_steps:
                onset_step = start
                peak_decel = float(np.min(a[start:]))
                events.append({
                    "traj": int(i),
                    "onset_step": int(onset_step),
                    "peak_decel": float(peak_decel),
                    "gap_m": float(logs.gap[i, onset_step]),
                    "closing_m_s": float(logs.v_ego[i, onset_step] - logs.v_lead_s[i, onset_step]),
                    "ego_speed": float(logs.v_ego[i, onset_step]),
                })
    return events


def human_brake_limit(logs, q=0.1):
    """Hardest braking [m/s^2, positive number] that the logged human followers ever applied (the q-th percentile of
    their acceleration, from the speed differences). Learned planners cannot have seen anything harder."""
    a = np.diff(logs.v_ego, axis=1) / C.DT
    return float(-np.nanpercentile(a, q))


def grid_from_logs(logs, v_ego, n_gap=60, n_dv=45):
    """Scenario grid. Gap limits come from what the logs contain (p2 .. p98 of the logged gaps). Closing speed runs
    from 0 to v_ego: dv = v_ego means the cutter is standing still, the most extreme case (never faster than that,
    otherwise the cutter would drive backwards)."""
    g_lo, g_hi = np.nanpercentile(logs.gap, [2, 98])
    return np.linspace(g_lo, g_hi, n_gap), np.linspace(0.0, v_ego, n_dv)
