# Which MESD version this study uses

**Used: the `MESD2.0/` folder at commit 5dcc2236ac5b5eeb6228503f544053c2a359b636 ("add cgs cgb cgd",
26 Dec 2025), the newest commit of the MESD repository when the study was run.** The repository holds
two folders with the same 44 device files: `MESD/` (the original release, tag v1.0.0 = commit 507d208,
26 Sep 2024, which contains only `MESD/`) and `MESD2.0/` (added on 26 Dec 2025 next to it).

## What differs (all 44 files compared value by value; per-file numbers in MESD_vs_MESD2.0_comparison.csv)

| | MESD (v1.0.0) | MESD2.0 (used) |
|---|---|---|
| fields per curve | Vgs, Vds, L, W, Temp, Corner, Ids, Cgg | the same + **Cgs, Cgd, Cgb** |
| curves, order, bias grid | identical | identical |
| Ids | reference | identical to 5 significant digits (largest relative difference 9e-5 above 1 fA; the rest is rounding of sub-fA leakage values) |
| Cgg, 7 of the 8 planar PDKs (N180A, N180B, N350A, N40A, N45B, N55A, N90A) | reference | identical to 5 significant digits (rounding only, largest relative difference 1.0e-4) |
| **Cgg, N45A** (both devices) | reference | **re-simulated: every curve differs, median relative difference 2-6 %, up to 95 % at single points** |
| N45A, N15A, N7A file header | has Node and Model (N45A: **BSIM4.0**) | Node and Model fields removed (the code takes the node from the file name) |

In MESD2.0, N45A is the only PDK whose stored Cgg equals Cgs + Cgd + Cgb (median mismatch 1e-4); in all
other planar PDKs the stored Cgs does not add up, which is the Cgs artefact documented by the Step 1
audit (paper Figure 1: stored Cgs follows gm/(2 pi f)). Cgs, Cgd and Cgb are therefore not used as
targets; only Ids and Cgg are.

## Consequences

* The Id study is the same under either version (Ids is identical to rounding).
* The Cgg study is defined on MESD2.0. Results for the N45A fold (and every split containing N45A
  curves) would differ slightly under v1.0.0. MESD2.0 is the authors' current release and its N45A Cgg
  is internally consistent (equals Cgs + Cgd + Cgb).

## Compact-model families

The MESD2.0 header of the N45A files has no `Model` field; the v1.0.0 header of the same files gives
`"Model": "BSIM4.0"`. The model-family control (Steps 10.4-10.5) therefore uses all five BSIM4 PDKs.
Families: BSIM3v3 = N90A, N180A, N350A; BSIM4.x = N40A (4.5), N45A (4.0), N45B (4.3), N55A (4.5),
N180B (4.5). This was the one amendment made during the study (code v9; see CHANGELOG.md and
records/AMENDMENTS.md).
