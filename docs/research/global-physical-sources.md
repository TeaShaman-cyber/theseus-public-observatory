# Global physical observations — source admission queue

Research coordination #14; federated read interface #44. Survey date
2026-11-28. The aim is independent instrument and geographic coverage,
not an artificial count of websites. All rows below are candidates unless
explicitly marked otherwise. Metadata discovery does not prove an API,
numeric coverage, access rights or long-term availability.

## Solar and geospace

| Candidate | Independent signal / lineage | Access and admission boundary |
|---|---|---|
| [XRAS / IKI–ISTP](https://xras.ru/about_site.html) | Operational solar and geomagnetic portal; mixed instrument provenance | Inventory individual products; mark republished GOES/NOAA and forecasts separately; no duplicate independent votes |
| [ISTP SB RAS observation archives](https://ru.iszf.irk.ru/Наблюдения) and [Badary](http://badary.iszf.irk.ru/) | Siberian solar radio observations, optical and geophysical instruments | Catalogue and bounded sample first; verify units, instrument identity, calibration, rights; no bulk mirror |
| [IKI solar radio spectropolarimeter](https://srsp.cosmos.ru/) | Ground-based radio spectra; distinguish own channels from displayed GOES | Verify numerical archive and instrument-specific data terms |
| [RATAN-600](https://rat.sao.ru/observation-archive/) | Solar radio spectral/polarization observations within a mixed archive dating to 1979 | Date/cabin search, filter solar products; no claim of uninterrupted solar coverage |
| [Russian space-weather source directory](https://spaceweather.ru/ru/content/datasets) | IZMIRAN, MSU SINP, IKI Interball, ISTP; directory not independent sensor | Trace original spacecraft/station per product; forecasts separate |
| [ASO-S / Kuafu-1](https://www.nssdc.ac.cn/nssdc_zh/html/task/asos.html) | Chinese solar vector magnetograph, Ly-alpha telescope, hard X-ray imager | [Science data browser](http://aso-s.pmo.ac.cn/sodc/imageBrowser.jsp); open release announced in 2023; exact product access/terms untested |
| [CHASE / Xihe](https://www.cas.cn/yx/202505/t20250514_5068195.shtml) | Independent solar spectral imaging | Dataset discovery and bounded product check, not automatic mirror |
| [Fengyun](https://data.nsmc.org.cn/DataPortal/en/data/dataset.html) | Chinese satellite atmospheric and space environment measurements | Registration/request form required for full data download; no enrollment attempted |
| [Chinese Meridian Project](https://www.meridianproject.ac.cn/en/) | Ground-based ionosondes, geomagnetic, radar, optical and atmospheric instruments | [Data portal](https://data.meridianproject.ac.cn/); station/product selection and access policy unverified |
| [WDC Beijing](https://wdc.geophys.ac.cn/About.asp) | Magnetometers, ionosondes, meteor radar, GPS; possible Meridian overlap | Track original station and avoid duplicate series |
| [INTERMAGNET](https://intermagnet.org/data_download) | Global geographically distributed magnetometer stations, independently measured X/Y/Z/F | HAPI verified below; [conditions](https://intermagnet.org/data_conditions.html); retain station/quality/coordinates, not one global aggregate |
| [SuperMAG](https://supermag.jhuapl.edu/) | Harmonized station magnetometer network and indices; overlaps INTERMAGNET | Registration and source lineage check; do not treat reprocessed stations as independent |
| [ESA Swarm](https://vires.services/) | Orbital magnetic field and plasma | Candidate selective product queries; authentication/product terms to verify |
| [GNSS TEC](https://catalog.data.gov/dataset/gps-total-electron-content-tec-2-hr-data) | Ionospheric electron content/maps derived from GNSS | Preserve map resolution, station lineage and quality; coverage not guaranteed |

NASA OMNI and GFZ already have separate working readers. NOAA operational
indices remain distinct from retrospective products. For a later global
cosmic-ray control, evaluate [NMDB](https://www.nmdb.eu/) neutron monitor
stations, not uncalibrated counts pooled across instruments.

## Earth-ionosphere resonator, lightning, atmosphere

Schumann resonances are global ELF cavity modes excited mainly by lightning.
The received modal frequency, amplitude and width depend on propagation,
ionospheric conductivity, source geography, local interference, station
response and season/local time. Global existence is not proof of uniform
local amplitude or biological/technological causation.

| Candidate | Data evidence | Admission boundary |
|---|---|---|
| [Tomsk SOS-70](https://sos70.ru/?page_id=48) | Public current plots of frequency/amplitude/Q, four modes; [long-term research](https://sos70.ru/?page_id=42) | Numeric archive and redistribution terms not verified; graph colors not calibrated measurements; timezone UTC+7 for local-time plots |
| [Sierra Nevada ELF](https://doi.org/10.1016/j.cageo.2022.105148) | March 2013–Feb 2017 raw and processed measurements, 10-minute mode parameters | Prefer [processed archive](https://digibug.ugr.es/handle/10481/71563), ~3.33 GB as listed; raw months ~2.6 GB; metadata and limited member selection first, never whole archive on VM |
| [Nagycenk, Hungary](https://zenodo.org/records/13220677) | Measured and modeled frequency series; independent electric channel | Measured 2023 three-mode reader verified (#50); longer monthly diurnal averages need distinct support; CC BY 4.0 |
| [Vernadsky Antarctic / SOUSY Arctic](https://zenodo.org/records/5919944) | Daily spectrogram and first-mode frequency PNG plots, 2002–2020 and 2013–2020 respectively | Source ReadMe.txt confirms image-only ZIP members; not admitted for numeric inference; seek underlying numerical series |
| [Syowa Antarctica / Japan NIPR](https://scidbase.nipr.ac.jp/modules/metadata/index.php?content_id=105&ml_lang=en) | 1–100 Hz ULF/ELF observations | Metadata known; actual numeric access and dates unknown |
| [WWLLN WGLC](https://doi.org/10.5194/essd-13-3219-2021) | Global gridded lightning density and stroke power, corrected for detection efficiency | [Versioned archive](https://zenodo.org/records/4774529), daily/monthly products; match resolution to SR estimand; no inferred hourly data from daily values |
| [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) | Atmospheric reanalysis: temperature, precipitation, wind, radiation | Model/reanalysis, not independent raw station evidence; bounded subset and terms first |

The first SR experiment should ask whether a common geomagnetic/ionospheric
perturbation is associated with cross-station residual mode changes after
accounting for lightning distribution, seasonal and local-time cycles,
instrument and environmental covariates. Compare multiple geographically
distinct stations, use station-specific baselines and event/block
resampling, account for multiple lags and dependence. No universal
frequency threshold or biological claim. Sierra Nevada and polar archives
overlap GFZ/OMNI; time support and WGLC availability must be verified before
predeclaring the experiment. SIF remains an independent branch.

## Verified bounded INTERMAGNET canary

Endpoint https://imag-data.bgs.ac.uk/GIN_V1/hapi ; catalog HTTP200,
3086 dataset IDs, 1404088 bytes. IDs include multiple quality levels,
cadences and coordinate representations for the same station; NOT 3086
independent instruments. Fixed five-minute window
2023-11-05 18:00–18:05 UTC; definitive/PT1M/xyzf.
Kakioka (kak, Japan) 5 valid vector/magnitude rows, 2173 bytes.
Hartland (had, UK) 5 valid rows, 2205 bytes, SHA256
9d900e12e0633c8ff7eb0526cfc2205eadf383b4f991e444ebc9f6ee1517980f.
Irkutsk (irt, Russia) 5 rows but all 99999 fill, zero valid;
2216 bytes, SHA256 c87b198a5223b53ebbbfa6f73d9b5cbeb59f41e643aec72b5961dfcd415bf895.
Lanzhou (lzh) and Tiksi (tik) returned HTTP400 on this request, not
evidence of station absence. Do not broaden quality class automatically.
No bulk download or new recurring collector. Next adapter: validate HAPI
vector shapes, fill/units, station metadata, date coverage and per-channel
missingness; then remote multistation queries alongside OMNI/GFZ.

Follow-up metadata explains the two HTTP400 responses: the listed
definitive Lanzhou series ends 2019-04-22 and Tiksi ends 1991-12-31,
outside the 2023 request. The Irkutsk series spans 1998–2024 but
has internal missing values. A common historical window within the
catalogued coverage, 2017-09-08 01:00–01:05 UTC, returned five valid
rows each for Lanzhou, Irkutsk and Kakioka. Exact response SHA-256:
Lanzhou b1c86f453d53a337b1cb1115ad193a192f201a63c200f5253b15d7062bbd4d60
(2175 bytes), Irkutsk 88f8a71c9151da0039cfa78b8b134db75c981737b0d9b1956c2842fa19998417
(2216 bytes), Kakioka cabae71ee1195a4fc60e6db9c8fd326fcb0da49eb9ad500084764d99f69bb4bd
(2173 bytes). These are transport/data feasibility witnesses, not a
statistical comparison. Actual station coverage must be checked per window.

NCK admission detail: [federated reader](federated-read.md#schumann-resonance-measured-frequencies-50). Polar archive ReadMe.txt (Zenodo 5919944) checked directly: daily frequencies are PNG plots, not a validated numerical table. Sierra Nevada processed month/sensor NPZ remains a separate candidate (about 43 MB per month/sensor per publication); inspect archive packaging and selective access before any download.
