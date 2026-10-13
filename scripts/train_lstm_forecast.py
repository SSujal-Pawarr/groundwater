"""
PyTorch LSTM Forecast Model Training Script
============================================
Trains a 2-layer LSTM with spatial-topographic embeddings and site-level
variance normalization that predicts groundwater levels at ANY arbitrary
future date.

Architecture:
    Sequence Input: [seq_len=30, features=6] (normalized level, obs flag, 4 Fourier terms)
    Horizon Input:  [horizon_features=9] (4 target Fourier terms, normalized year,
                     normalized lat, lon, elevation, log-scaled site variance)
    LSTM:           hidden=128, num_layers=2, dropout=0.2
    Conditioning:   Concat(last_hidden, horizon_feat) → LayerNorm → GELU → 128 → 64 → 1 (delta_norm)

Evaluation:
    Evaluated in physical meters using each site's specific standard deviation (sigma).

Usage:
    python scripts/train_lstm_forecast.py

Output:
    models/advanced_forecast/maharashtra_lstm.pt
    models/advanced_forecast/maharashtra_lstm_meta.json
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger("train_lstm")

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "maharashtra" / "maharashtra_normalized.parquet"
MODEL_DIR = ROOT / "models" / "advanced_forecast"
MODEL_PATH = MODEL_DIR / "maharashtra_lstm.pt"
META_PATH = MODEL_DIR / "maharashtra_lstm_meta.json"

SEQ_LEN = 30
SEQ_FEATURES = 6
HORIZON_FEATURES = 9
HIDDEN = 128
NUM_LAYERS = 2
DROPOUT = 0.2
BATCH_SIZE = 256
EPOCHS = 18
LR = 2.5e-3
TEST_SPLIT_RATIO = 0.20
MIN_SITE_OBS = 30
ORIGIN_SAMPLE_STEP = 5
MIN_HORIZON_DAYS = 7
MAX_HORIZON_DAYS = 1100
TARGET_OFFSET_STEP = 8


def _fourier(doy: float | np.ndarray) -> tuple:
    angle = 2 * math.pi * np.asarray(doy, dtype=np.float32) / 365.25
    return np.sin(angle), np.cos(angle), np.sin(2 * angle), np.cos(2 * angle)


def _load_daily() -> pd.DataFrame:
    LOGGER.info("Loading Maharashtra daily data from %s", DATA_PATH)
    df = pd.read_parquet(DATA_PATH)
    if "is_analytics_ready" in df.columns:
        df = df[df["is_analytics_ready"].astype(bool)]
    df = df[df["water_level_raw"].notna()].copy()
    df["date"] = pd.to_datetime(df["observation_timestamp"]).dt.normalize()
    agg = (
        df.groupby(["candidate_site_id", "date"], sort=True)
        .agg(
            water_level=("water_level_raw", "mean"),
            lat=("latitude", "first"),
            lon=("longitude", "first"),
            elevation=("elevation_msl", "first"),
        )
        .reset_index()
    )
    agg["date"] = pd.to_datetime(agg["date"])
    LOGGER.info("Loaded %d daily records, %d sites", len(agg), agg["candidate_site_id"].nunique())
    return agg.sort_values(["candidate_site_id", "date"]).reset_index(drop=True)


class LSTMForecast(nn.Module):
    def __init__(self, seq_feat=SEQ_FEATURES, hor_feat=HORIZON_FEATURES, hidden=HIDDEN, num_layers=NUM_LAYERS, dropout=DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=seq_feat,
            hidden_size=hidden,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden + hor_feat, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, 1),
        )

    def forward(self, seq, hor):
        _, (h_n, _) = self.lstm(seq)
        last_hidden = h_n[-1]
        combined = torch.cat([last_hidden, hor], dim=1)
        return self.fc(combined)


def build_dataset(daily: pd.DataFrame, split_date: pd.Timestamp):
    train_seqs, train_horizons, train_deltas = [], [], []
    test_seqs, test_horizons, test_deltas, test_sigmas = [], [], [], []
    site_norms = {}

    lat_mean = float(daily["lat"].mean() or 19.5)
    lat_std = float(daily["lat"].std() or 2.0) + 1e-4
    lon_mean = float(daily["lon"].mean() or 76.0)
    lon_std = float(daily["lon"].std() or 2.0) + 1e-4
    elev_mean = float(daily["elevation"].fillna(0).mean() or 400.0)
    elev_std = float(daily["elevation"].fillna(0).std() or 150.0) + 1e-4

    spatial_stats = {
        "lat_mean": lat_mean, "lat_std": lat_std,
        "lon_mean": lon_mean, "lon_std": lon_std,
        "elev_mean": elev_mean, "elev_std": elev_std,
    }

    sites = daily["candidate_site_id"].unique()
    for site_id in sites:
        s = daily[daily["candidate_site_id"] == site_id].set_index("date")
        if len(s) < MIN_SITE_OBS:
            continue
        full_idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
        levels = s["water_level"].reindex(full_idx).values.astype(np.float32)

        train_mask = full_idx < split_date
        train_levels = levels[train_mask]
        valid_train = train_levels[~np.isnan(train_levels)]
        if len(valid_train) < 2:
            continue
        mu = float(np.mean(valid_train))
        sigma = float(np.std(valid_train) + 1e-4)

        lat = float(s["lat"].iloc[0]) if s["lat"].notna().any() else lat_mean
        lon = float(s["lon"].iloc[0]) if s["lon"].notna().any() else lon_mean
        elev = float(s["elevation"].iloc[0]) if s["elevation"].notna().any() else elev_mean

        site_norms[site_id] = {
            "mean": mu, "std": sigma,
            "lat": lat, "lon": lon, "elevation": elev,
        }

        norm_lat = (lat - lat_mean) / lat_std
        norm_lon = (lon - lon_mean) / lon_std
        norm_elev = (elev - elev_mean) / elev_std
        norm_std = np.log1p(sigma) / 2.0

        has_obs = (~np.isnan(levels)).astype(np.float32)
        levels_norm = np.where(np.isnan(levels), 0.0, (levels - mu) / sigma)

        for i in range(SEQ_LEN, len(full_idx), ORIGIN_SAMPLE_STEP):
            origin_level_raw = levels[i]
            if np.isnan(origin_level_raw):
                continue

            seq_slice = slice(i - SEQ_LEN, i)
            seq_doys = np.array([d.day_of_year for d in full_idx[seq_slice]], dtype=np.float32)
            sa, ca, ss, cs = _fourier(seq_doys)
            seq_feat = np.stack([
                levels_norm[seq_slice],
                has_obs[seq_slice],
                sa, ca, ss, cs,
            ], axis=1)

            future_offsets = range(MIN_HORIZON_DAYS, min(MAX_HORIZON_DAYS, len(full_idx) - i), TARGET_OFFSET_STEP)
            for offset in future_offsets:
                j = i + offset
                if j >= len(full_idx):
                    break
                target_date = full_idx[j]
                target_level_raw = levels[j]
                if np.isnan(target_level_raw):
                    continue
                delta_raw = target_level_raw - origin_level_raw
                if abs(delta_raw) > 25.0:  # sensor anomaly filter
                    continue
                delta_norm = delta_raw / sigma

                t_doy = target_date.day_of_year
                t_year_norm = (target_date.year - 2020) / 5.0
                tsa, tca, tss, tcs = _fourier(float(t_doy))
                horizon_feat = np.array([
                    tsa, tca, tss, tcs, t_year_norm,
                    norm_lat, norm_lon, norm_elev, norm_std
                ], dtype=np.float32)

                if target_date < split_date:
                    train_seqs.append(seq_feat.astype(np.float32))
                    train_horizons.append(horizon_feat)
                    train_deltas.append(float(delta_norm))
                else:
                    test_seqs.append(seq_feat.astype(np.float32))
                    test_horizons.append(horizon_feat)
                    test_deltas.append(float(delta_norm))
                    test_sigmas.append(sigma)

    LOGGER.info("Train samples: %d | Test samples: %d", len(train_seqs), len(test_seqs))

    X_seq_tr = torch.tensor(np.array(train_seqs), dtype=torch.float32)
    X_hor_tr = torch.tensor(np.array(train_horizons), dtype=torch.float32)
    y_tr = torch.tensor(np.array(train_deltas), dtype=torch.float32).unsqueeze(1)

    X_seq_te = torch.tensor(np.array(test_seqs), dtype=torch.float32)
    X_hor_te = torch.tensor(np.array(test_horizons), dtype=torch.float32)
    y_te = torch.tensor(np.array(test_deltas), dtype=torch.float32).unsqueeze(1)
    sigmas_te = np.array(test_sigmas, dtype=np.float32)

    return (X_seq_tr, X_hor_tr, y_tr), (X_seq_te, X_hor_te, y_te, sigmas_te), site_norms, spatial_stats


def train(train_data, test_data, site_norms):
    X_seq_tr, X_hor_tr, y_tr = train_data
    X_seq_te, X_hor_te, y_te, sigmas_te = test_data

    model = LSTMForecast(SEQ_FEATURES, HORIZON_FEATURES, HIDDEN, NUM_LAYERS, DROPOUT)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.HuberLoss(delta=1.0)

    train_loader = DataLoader(
        TensorDataset(X_seq_tr, X_hor_tr, y_tr),
        batch_size=BATCH_SIZE, shuffle=True,
    )
    test_loader = DataLoader(
        TensorDataset(X_seq_te, X_hor_te, y_te),
        batch_size=BATCH_SIZE * 2, shuffle=False,
    )

    LOGGER.info("Training LSTM for %d epochs...", EPOCHS)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        for s_b, h_b, y_b in train_loader:
            optimizer.zero_grad()
            p = model(s_b, h_b)
            loss = criterion(p, y_b)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item() * len(s_b)
        epoch_loss /= len(X_seq_tr)
        scheduler.step()

        if epoch % 3 == 0 or epoch == 1:
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for s_b, h_b, y_b in test_loader:
                    v_p = model(s_b, h_b)
                    val_loss += criterion(v_p, y_b).item() * len(s_b)
            val_loss /= len(X_seq_te)
            LOGGER.info("Epoch %2d/%d | train loss: %.4f | val loss: %.4f", epoch, EPOCHS, epoch_loss, val_loss)

    # Batched test evaluation in physical meters
    model.eval()
    preds_norm_list = []
    with torch.no_grad():
        for s_b, h_b, _ in test_loader:
            preds_norm_list.append(model(s_b, h_b).numpy().flatten())
    preds_norm = np.concatenate(preds_norm_list)
    trues_norm = y_te.numpy().flatten()

    # De-normalize to physical meters using per-sample sigma
    preds_m = preds_norm * sigmas_te
    trues_m = trues_norm * sigmas_te

    e = preds_m - trues_m
    ss_tot = np.sum((trues_m - trues_m.mean()) ** 2)

    test_metrics = {
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "r2": float(1 - np.sum(e ** 2) / ss_tot) if ss_tot > 0 else float("nan"),
        "n": int(len(trues_m)),
    }

    e_pers = trues_m
    pers_metrics = {
        "mae": float(np.mean(np.abs(e_pers))),
        "rmse": float(np.sqrt(np.mean(e_pers ** 2))),
    }

    LOGGER.info(
        "LSTM test in physical meters: MAE=%.3f m  RMSE=%.3f m  R2=%.4f  (skill vs persist MAE: %+.1f%%, RMSE: %+.1f%%)",
        test_metrics["mae"], test_metrics["rmse"], test_metrics["r2"],
        100 * (1 - test_metrics["mae"] / pers_metrics["mae"]),
        100 * (1 - test_metrics["rmse"] / pers_metrics["rmse"]),
    )
    return model, test_metrics, pers_metrics


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    daily = _load_daily()

    all_dates = sorted(daily["date"].unique())
    split_date = pd.Timestamp(all_dates[int(len(all_dates) * (1 - TEST_SPLIT_RATIO))])
    LOGGER.info("Chronological split date: %s", split_date.date())

    train_data, test_data, site_norms, spatial_stats = build_dataset(daily, split_date)
    if len(train_data[0]) == 0:
        LOGGER.error("No training samples built. Check data path.")
        return 1

    model, test_metrics, pers_metrics = train(train_data, test_data, site_norms)

    # Save artifact
    torch.save({
        "model_state_dict": model.state_dict(),
        "model_config": {
            "seq_features": SEQ_FEATURES,
            "horizon_features": HORIZON_FEATURES,
            "hidden": HIDDEN,
            "num_layers": NUM_LAYERS,
            "dropout": DROPOUT,
            "seq_len": SEQ_LEN,
        },
        "site_norms": site_norms,
        "spatial_stats": spatial_stats,
        "data_through": str(daily["date"].max().date()),
        "test_metrics": test_metrics,
        "persist_metrics": pers_metrics,
        "split_date": str(split_date.date()),
    }, MODEL_PATH)
    LOGGER.info("Saved LSTM model to %s", MODEL_PATH)

    meta = {
        "model_type": "pytorch_lstm",
        "region": "maharashtra",
        "seq_len": SEQ_LEN,
        "hidden": HIDDEN,
        "num_layers": NUM_LAYERS,
        "data_through": str(daily["date"].max().date()),
        "test_metrics": test_metrics,
        "persist_metrics": pers_metrics,
        "split_date": str(split_date.date()),
        "n_sites": len(site_norms),
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    LOGGER.info("Saved LSTM metadata to %s", META_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
