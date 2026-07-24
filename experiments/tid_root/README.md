# TID Observatory root pilot: GW150914

This experiment replays the April 28 root idea on public raw data without using historical TID target values as acceptance criteria.

## Measurement boundary

- Source: public GWOSC/LOSC GW150914 H1/L1 strain, 32 s, 16 kHz.
- Event window and four off-event control windows are fixed before feature inspection.
- Identical feature extraction is applied to event and controls.
- Historical values such as 0.382/0.618 are provenance claims under test, never classifier targets.
- Output is measurement evidence, not a claim of new gravitational-wave physics.

## Features

- DFA/Hurst-like scaling from q=2 MFDFA slope
- multifractal spectrum width candidate (`delta_alpha`)
- PSD log-log slope
- sample entropy
- H1/L1 magnitude-squared coherence

The first run is deliberately small. Four controls provide an empirical rank only; they are not enough for a calibrated p-value.
