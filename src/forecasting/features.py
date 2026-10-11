"""
Leak-free feature construction.
Every feature for an origin (site, date) uses ONLY information with date <= origin date.
Targets are attached separately in pairs.py.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

F32 = np.float32


# --------------------------------------------------------------------------------------
# Maharashtra: dense daily grid
# --------------------------------------------------------------------------------------
MH_FEATURES = [
    "cur", "chg_1", "chg_3", "chg_7", "chg_14", "std_7", "mean_14_minus_cur",
    "exp_mean", "exp_std", "exp_min", "exp_max", "cur_minus_exp_mean", "cur_z", "n_hist",
    "district_chg_7", "district_chg_14", "precip_sum_7d", "precip_sum_30d",
    "lat", "lon", "elevation",
]


def build_features_mh(obs: pd.DataFrame) -> pd.DataFrame:
    sites = pd.Index(sorted(obs["candidate_site_id"].unique()), name="candidate_site_id")
    days = pd.date_range(obs["date"].min(), obs["date"].max(), freq="D")
    pv = obs.pivot(index="candidate_site_id", columns="date", values="value").reindex(index=sites, columns=days)
    meta = obs.groupby("candidate_site_id").agg(lat=("lat", "first"), lon=("lon", "first"),
                                                 elevation=("elevation", "first"), district=("district", "first")).reindex(sites)
    T = pv.T  # days x sites

    def chg(k):
        return (T - T.shift(k))

    c1, c3, c7, c14 = chg(1), chg(3), chg(7), chg(14)
    std7 = T.rolling(7, min_periods=4).std()
    mean14 = T.rolling(14, min_periods=7).mean()
    exp_mean = T.expanding(min_periods=3).mean()
    exp_std = T.expanding(min_periods=3).std()
    exp_min = T.expanding(min_periods=3).min()
    exp_max = T.expanding(min_periods=3).max()
    n_hist = T.notna().cumsum()

    dist = meta["district"].fillna("UNK").values
    d7 = c7.T.groupby(dist).transform("mean").T
    d14 = c14.T.groupby(dist).transform("mean").T

    def pivot_opt(col):
        if col in obs.columns:
            return obs.pivot(index="candidate_site_id", columns="date", values=col).reindex(index=sites, columns=days).T
        return pd.DataFrame(np.nan, index=days, columns=sites)

    p7, p30 = pivot_opt("precip_sum_7d"), pivot_opt("precip_sum_30d")

    shape = T.shape
    def flat(df): return df.values.ravel()
    lat = np.broadcast_to(meta["lat"].values, shape).ravel()
    lon = np.broadcast_to(meta["lon"].values, shape).ravel()
    elev = np.broadcast_to(meta["elevation"].values, shape).ravel()
    site_col = np.broadcast_to(sites.values, shape).ravel()
    date_col = np.broadcast_to(days.values[:, None], shape).ravel()

    cur = flat(T)
    es = flat(exp_std)
    out = pd.DataFrame({
        "candidate_site_id": site_col, "date": date_col, "cur": cur,
        "chg_1": flat(c1), "chg_3": flat(c3), "chg_7": flat(c7), "chg_14": flat(c14),
        "std_7": flat(std7), "mean_14_minus_cur": flat(mean14) - cur,
        "exp_mean": flat(exp_mean), "exp_std": es, "exp_min": flat(exp_min), "exp_max": flat(exp_max),
        "cur_minus_exp_mean": cur - flat(exp_mean),
        "cur_z": np.where(es > 1e-9, (cur - flat(exp_mean)) / np.where(es > 1e-9, es, 1), np.nan),
        "n_hist": flat(n_hist), "district_chg_7": flat(d7), "district_chg_14": flat(d14),
        "precip_sum_7d": flat(p7), "precip_sum_30d": flat(p30),
        "lat": lat, "lon": lon, "elevation": elev,
    })
    out = out[out["cur"].notna()].reset_index(drop=True)
    out["group_origin"] = "ALL"
    for c in MH_FEATURES:
        out[c] = out[c].astype(F32)
    return out


# --------------------------------------------------------------------------------------
# India: sparse, ~quarterly observations
# --------------------------------------------------------------------------------------
INDIA_FEATURES = [
    "cur", "chg_1obs", "days_1obs", "chg_2obs", "chg_4obs", "days_4obs", "chg_8obs", "days_8obs",
    "chg_vs_ly", "chg_vs_ly2", "ly_level", "exp_mean", "exp_std", "cur_minus_exp_mean", "n_hist",
    "grp_mean", "cur_minus_grp_mean", "grp_n", "district_chg_ly", "origin_month", "lat", "lon",
]


def _asof_lookup(obs: pd.DataFrame, shift_days: int, tol_days: int) -> np.ndarray:
    left = pd.DataFrame({
        "candidate_site_id": obs["candidate_site_id"].values,
        "key": obs["date"].values - np.timedelta64(shift_days, "D"),
        "_i": np.arange(len(obs)),
    }).sort_values("key")
    right = obs[["candidate_site_id", "date", "value"]].rename(columns={"date": "_rdate", "value": "_rval"}).sort_values("_rdate")
    m = pd.merge_asof(left, right, left_on="key", right_on="_rdate", by="candidate_site_id",
                      tolerance=pd.Timedelta(days=tol_days), direction="nearest")
    out = np.full(len(obs), np.nan)
    out[m["_i"].values] = m["_rval"].values
    return out


def build_features_india(obs: pd.DataFrame) -> pd.DataFrame:
    obs = obs.sort_values(["candidate_site_id", "date"]).reset_index(drop=True)
    g = obs.groupby("candidate_site_id", sort=False)
    v = obs["value"]
    cur = v.values.astype("float64")
    d = obs["date"]

    def lag(k): return g["value"].shift(k).values
    def dlag(k): return (d - g["date"].shift(k)).dt.days.values

    n = g.cumcount().values + 1
    cs = g["value"].cumsum().values
    cs2 = (v ** 2).groupby(obs["candidate_site_id"], sort=False).cumsum().values
    exp_mean = cs / n
    exp_var = np.maximum(cs2 / n - exp_mean ** 2, 0) * n / np.maximum(n - 1, 1)
    gg = obs.groupby(["candidate_site_id", "group"], sort=False)
    gn = gg.cumcount().values + 1
    grp_mean = gg["value"].cumsum().values / gn

    ly = _asof_lookup(obs, 365, 60)
    ly2 = _asof_lookup(obs, 730, 60)
    chg_ly = cur - ly
    yr, mo = d.dt.year.values, d.dt.month.values
    tmp = pd.DataFrame({"dist": obs["district"].fillna("UNK").values, "yr": yr, "mo": mo, "x": chg_ly})
    district_chg_ly = tmp.groupby(["dist", "yr", "mo"])["x"].transform("mean").values

    out = pd.DataFrame({
        "candidate_site_id": obs["candidate_site_id"].values, "date": d.values, "cur": cur,
        "chg_1obs": cur - lag(1), "days_1obs": dlag(1), "chg_2obs": cur - lag(2),
        "chg_4obs": cur - lag(4), "days_4obs": dlag(4), "chg_8obs": cur - lag(8), "days_8obs": dlag(8),
        "chg_vs_ly": chg_ly, "chg_vs_ly2": cur - ly2, "ly_level": ly,
        "exp_mean": exp_mean, "exp_std": np.sqrt(exp_var), "cur_minus_exp_mean": cur - exp_mean, "n_hist": n,
        "grp_mean": grp_mean, "cur_minus_grp_mean": cur - grp_mean, "grp_n": gn,
        "district_chg_ly": district_chg_ly, "origin_month": mo,
        "lat": obs["lat"].values, "lon": obs["lon"].values,
    })
    out["group_origin"] = obs["group"].values
    for c in INDIA_FEATURES:
        out[c] = out[c].astype(F32)
    return out


def feature_columns(region: str):
    return MH_FEATURES if region == "maharashtra" else INDIA_FEATURES


def build_features(region: str, obs: pd.DataFrame) -> pd.DataFrame:
    return build_features_mh(obs) if region == "maharashtra" else build_features_india(obs)


# --------------------------------------------------------------------------------------
# Percentile of a value against a site's own history known at the origin
# --------------------------------------------------------------------------------------
def reference_percentile(obs: pd.DataFrame, q_site, q_date, q_group, q_value, min_ref: int) -> np.ndarray:
    """
    percentile = (less + 0.5*equal) / n * 100 over the site's observations with
    date <= q_date AND group == q_group. NaN if n < min_ref.
    Same definition as the M8.2-D condition engine (expanding percentile), but anchored at the forecast origin.
    """
    obs = obs.sort_values(["candidate_site_id", "date"])
    gmap = {g: i for i, g in enumerate(pd.unique(pd.concat([obs["group"].astype(str), pd.Series(q_group).astype(str)])))}
    o_g = obs["group"].astype(str).map(gmap).values
    o_d = obs["date"].values.astype("datetime64[ns]").astype("int64")
    o_v = obs["value"].values.astype("float64")
    _sorted_sites = obs["candidate_site_id"].values
    _st, _en = _site_bounds(_sorted_sites)
    site_start = {_sorted_sites[a]: (a, b) for a, b in zip(_st, _en)}

    q_site = np.asarray(q_site)
    q_d = np.asarray(q_date, dtype="datetime64[ns]").astype("int64")
    q_g = pd.Series(q_group).astype(str).map(gmap).values
    q_v = np.asarray(q_value, dtype="float64")
    out = np.full(len(q_site), np.nan)

    order = np.argsort(q_site, kind="stable")
    qs_sorted = q_site[order]
    bounds_s, bounds_e = _site_bounds(qs_sorted)
    uniq_sites = qs_sorted[bounds_s]
    for s, a, b in zip(uniq_sites, bounds_s, bounds_e):
        if s not in site_start:
            continue
        ra, rb = site_start[s]
        idx = order[a:b]
        rd, rg, rv = o_d[ra:rb], o_g[ra:rb], o_v[ra:rb]
        mask = (rd[None, :] <= q_d[idx][:, None]) & (rg[None, :] == q_g[idx][:, None])
        n_ref = mask.sum(1)
        less = (mask & (rv[None, :] < q_v[idx][:, None])).sum(1)
        eq = (mask & (rv[None, :] == q_v[idx][:, None])).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            p = (less + 0.5 * eq) / n_ref * 100.0
        p[(n_ref < min_ref) | np.isnan(q_v[idx])] = np.nan
        out[idx] = p
    return out


def _site_bounds(sorted_sites: np.ndarray):
    if len(sorted_sites) == 0:
        return np.array([], int), np.array([], int)
    change = np.flatnonzero(sorted_sites[1:] != sorted_sites[:-1]) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [len(sorted_sites)]])
    return starts, ends
