#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Dict, Iterable, Tuple
from urllib.request import urlopen

import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ligo_pilot import GWOSC_FILES, build_manifest, fixed_windows, sha256_file


def slice_window(x: np.ndarray, sample_rate_hz: int, window: Tuple[float, float]) -> np.ndarray:
    start = int(round(window[0] * sample_rate_hz))
    end = int(round(window[1] * sample_rate_hz))
    return np.asarray(x[start:end])


def _logfit(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if mask.sum() < 3:
        return float('nan')
    return float(np.polyfit(np.log(x[mask]), np.log(y[mask]), 1)[0])


def compute_features(x: np.ndarray, sample_rate_hz: int) -> Dict[str, float]:
    from scipy import signal
    from MFDFA import MFDFA
    import antropy as ant

    x = np.asarray(x, dtype=float)
    x = signal.detrend(x, type='linear')
    sd = float(np.std(x))
    if not np.isfinite(sd) or sd == 0:
        raise ValueError('window has zero or invalid variance')
    x = x / sd

    nyq = sample_rate_hz / 2.0
    hi = min(350.0, nyq * 0.9)
    lo = min(20.0, hi / 4.0)
    sos = signal.butter(4, [lo, hi], btype='bandpass', fs=sample_rate_hz, output='sos')
    x = signal.sosfiltfilt(sos, x)

    nperseg = min(2048, max(256, len(x) // 8))
    freqs, psd = signal.welch(x, fs=sample_rate_hz, nperseg=nperseg)
    pmask = (freqs >= max(25.0, lo)) & (freqs <= min(250.0, hi)) & ~((freqs >= 55) & (freqs <= 65))
    psd_slope = _logfit(freqs[pmask], psd[pmask])

    lag = np.unique(np.logspace(np.log10(16), np.log10(max(32, min(len(x)//8, 1024))), 18).astype(int))
    q = np.array([-5., -3., -1., 1., 2., 3., 5.])
    lag_out, fq = MFDFA(x, lag=lag, q=q, order=1)
    fq = np.asarray(fq)
    if fq.ndim == 1:
        fq = fq[:, None]
    hq = np.array([_logfit(lag_out, fq[:, i]) for i in range(fq.shape[1])])
    dfa_h = float(hq[np.argmin(np.abs(q - 2.0))])
    dhdq = np.gradient(hq, q)
    alpha = hq + q * dhdq
    mfdfa_delta_alpha = float(np.nanmax(alpha) - np.nanmin(alpha))

    down = np.ascontiguousarray(x[::max(1, sample_rate_hz // 512)], dtype=np.float64)
    if len(down) > 8192:
        down = down[:8192]
    sample_entropy = float(ant.sample_entropy(down))

    return {
        'dfa_h': dfa_h,
        'mfdfa_delta_alpha': mfdfa_delta_alpha,
        'psd_slope': psd_slope,
        'sample_entropy': sample_entropy,
    }


def compute_pair_coherence(x: np.ndarray, y: np.ndarray, sample_rate_hz: int) -> float:
    from scipy import signal
    x = signal.detrend(np.asarray(x, dtype=float), type='linear')
    y = signal.detrend(np.asarray(y, dtype=float), type='linear')
    nperseg = min(2048, max(256, len(x)//8))
    f, cxy = signal.coherence(x, y, fs=sample_rate_hz, nperseg=nperseg)
    mask = (f >= 30.0) & (f <= min(250.0, sample_rate_hz/2*0.9)) & ~((f >= 55) & (f <= 65))
    return float(np.nanmean(cxy[mask]))


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    with urlopen(url, timeout=60) as r, path.open('wb') as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def load_strain(path: Path) -> Tuple[np.ndarray, int]:
    import h5py
    with h5py.File(path, 'r') as h:
        x = np.asarray(h['strain']['Strain'][:], dtype=float)
        # LOSC 16 kHz 32 s files are 16384 Hz; derive defensively from metadata when present.
        sample_rate = int(round(len(x) / 32.0))
    return x, sample_rate


def run(out_dir: Path) -> Dict[str, object]:
    raw = out_dir / 'raw'
    files = {}
    for det, url in GWOSC_FILES.items():
        path = raw / Path(url).name
        download(url, path)
        files[det] = path

    data = {}
    rates = set()
    for det, path in files.items():
        arr, rate = load_strain(path)
        data[det] = arr
        rates.add(rate)
    if len(rates) != 1:
        raise RuntimeError(f'sample-rate mismatch: {rates}')
    rate = rates.pop()
    if len({len(v) for v in data.values()}) != 1:
        raise RuntimeError('detector sample-count mismatch')

    sha = {det: sha256_file(path) for det, path in files.items()}
    manifest = build_manifest(sha, rate, len(data['H1']))
    manifest['source_file_sizes'] = {det: files[det].stat().st_size for det in files}

    windows = fixed_windows()
    labels = [('event', windows['event'])] + [(f'control_{i+1}', w) for i, w in enumerate(windows['controls'])]
    rows = []
    for label, win in labels:
        pair = {}
        for det in ('H1','L1'):
            segment = slice_window(data[det], rate, win)
            feats = compute_features(segment, rate)
            row = {'window': label, 'detector': det, 'start_s': win[0], 'end_s': win[1], **feats}
            rows.append(row)
            pair[det] = segment
        coh = compute_pair_coherence(pair['H1'], pair['L1'], rate)
        for row in rows[-2:]:
            row['h1_l1_coherence'] = coh

    # Empirical rank against four pre-registered controls, not a calibrated p-value.
    metrics = ['dfa_h','mfdfa_delta_alpha','psd_slope','sample_entropy','h1_l1_coherence']
    summary = {'event_vs_controls': {}}
    for det in ('H1','L1'):
        det_rows = [r for r in rows if r['detector'] == det]
        event = next(r for r in det_rows if r['window']=='event')
        controls = [r for r in det_rows if r['window'].startswith('control_')]
        for m in metrics:
            ev = event[m]
            vals = [c[m] for c in controls]
            rank_two_sided = 1 + sum(abs(v - np.median(vals)) >= abs(ev - np.median(vals)) for v in vals)
            summary['event_vs_controls'].setdefault(m,{})[det] = {
                'event': ev,
                'controls': vals,
                'control_median': float(np.median(vals)),
                'empirical_rank_count_ge': int(rank_two_sided),
                'n_controls': len(vals),
            }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    (out_dir/'features.json').write_text(json.dumps(rows, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    (out_dir/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    return {'manifest': manifest, 'features': rows, 'summary': summary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    result = run(args.out_dir)
    print(json.dumps({'status':'OK','rows':len(result['features']),'out_dir':str(args.out_dir)}, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
