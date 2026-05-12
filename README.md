[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20148091.svg)](https://doi.org/10.5281/zenodo.20148091)

# SPDR Verification Suite

**24 Kodak Images. 73% Smaller Through Facebook's JPEG Pipeline. Verify It Yourself.**

> Upstream RGB covariance reshaping produces visually identical images that encode at 0.95-1.79 BPP through Facebook's pipeline - a 73% mean reduction across the full Kodak PCD0992 suite.

This repository contains 24 processed versions of the Kodak Lossless True Color Image Suite alongside their Facebook pipeline outputs and the unmodified originals for direct comparison. Every image is a standard JPEG readable by any existing decoder. Every measurement is independently reproducible.

Jasmine Baetzel (2026)

---

## Quick Verification

```bash
git clone https://github.com/PearsonZero/kodak-pcd0992-spdr-verification-suite.git
cd kodak-pcd0992-spdr-verification-suite
pip install numpy Pillow
python3 scripts/verify_suite.py
```

The script measures every image in the repository and compares the results against the published JSON data. Total runtime: approximately 2 minutes. No configuration required.

To verify the Facebook pipeline results yourself: upload any image from `images/clean/` to Facebook (as a photo post or message attachment), download the recompressed output, and run:

```bash
python3 scripts/batch_measure.py path/to/downloaded/image.jpg
```

Compare the output against the corresponding JSON in `data/json/fb1/` or `data/json/fb2/`.

---

## Results

### Suite Summary

| Metric | SPDR Source | FB Pipeline Output |
|---|---|---|
| Mean BPP | 4.803 | 1.312 |
| Mean Avg \|r\| | 0.8473 | 0.8482 |
| Mean BPP Reduction | - | 72.7% |
| BPP Range | 3.96-6.04 | 0.95-1.79 |
| Reduction Range | - | 68.5%-76.8% |

### Per-Image Results

| Image | Source BPP | FB1 BPP | FB2 BPP | Reduction | Avg \|r\| |
|---|---|---|---|---|---|
| kodim01 | 5.191 | 1.400 | 1.416 | 73.0% | 0.891 |
| kodim02 | 5.628 | 1.775 | 1.790 | 68.5% | 0.613 |
| kodim03 | 3.962 | 1.024 | 1.033 | 74.2% | 0.546 |
| kodim04 | 4.637 | 1.287 | 1.295 | 72.2% | 0.722 |
| kodim05 | 5.707 | 1.396 | 1.417 | 75.5% | 0.890 |
| kodim06 | 4.958 | 1.491 | 1.513 | 69.9% | 0.975 |
| kodim07 | 4.240 | 1.126 | 1.138 | 73.4% | 0.831 |
| kodim08 | 5.658 | 1.459 | 1.481 | 74.2% | 0.947 |
| kodim09 | 4.333 | 1.151 | 1.159 | 73.4% | 0.855 |
| kodim10 | 4.465 | 1.221 | 1.230 | 72.7% | 0.940 |
| kodim11 | 4.555 | 1.337 | 1.347 | 70.6% | 0.858 |
| kodim12 | 4.021 | 1.106 | 1.116 | 72.5% | 0.916 |
| kodim13 | 6.040 | 1.569 | 1.594 | 74.0% | 0.967 |
| kodim14 | 5.078 | 1.386 | 1.398 | 72.7% | 0.660 |
| kodim15 | 4.415 | 1.174 | 1.182 | 73.4% | 0.898 |
| kodim16 | 4.236 | 1.229 | 1.240 | 71.0% | 0.931 |
| kodim17 | 4.384 | 1.212 | 1.224 | 72.4% | 0.968 |
| kodim18 | 5.526 | 1.526 | 1.549 | 72.4% | 0.845 |
| kodim19 | 4.841 | 1.395 | 1.410 | 71.2% | 0.913 |
| kodim20 | 4.089 | 0.948 | 0.958 | 76.8% | 0.978 |
| kodim21 | 4.868 | 1.414 | 1.428 | 71.0% | 0.833 |
| kodim22 | 5.158 | 1.431 | 1.445 | 72.3% | 0.852 |
| kodim23 | 4.270 | 1.019 | 1.029 | 76.1% | 0.572 |
| kodim24 | 5.001 | 1.410 | 1.430 | 71.8% | 0.958 |

The suite spans the full spectrum of inter-channel correlation structure - from highly one-dimensional images (kodim20, Avg |r| = 0.978) to strongly three-dimensional images (kodim03, Avg |r| = 0.546). BPP reduction is consistent across all covariance geometries.

---

## Double-Pass Pipeline Stability

Each image was passed through Facebook's JPEG recompression pipeline twice (FB1 and FB2). The covariance geometry is stable through both passes - Avg |r| values match to the fourth decimal place between FB1 and FB2 across all 24 images. FB2 file sizes increase by an average of 1.5% relative to FB1, consistent with trivial re-encoding overhead. The compression geometry established by upstream reshaping does not degrade through repeated lossy encoding.

---

## What This Is Not

This is not a new codec. This is not a neural network. This is not a JPEG quality reduction.

The images in this repository are standard JPEG files. They are processed upstream of any colorspace conversion or compression pipeline. Every encoder and decoder in the delivery chain is unmodified. The BPP reduction occurs because the inter-channel covariance geometry of the pixel data has been reshaped before the encoder sees it.

The theoretical basis for this effect is documented across four prior papers in this series. Standard JPEG converts RGB to YCbCr using the BT.601 transform - a fixed linear rotation designed as a one-size-fits-all decorrelation step. The Karhunen-Loeve Transform (KLT) defines the optimal decorrelation for any given image, but it is image-specific and therefore impractical inside a fixed-format codec. The gap between BT.601's fixed axes and each image's KLT-optimal axes determines how much inter-channel redundancy passes through to the frequency domain untouched. SPDR reshapes the covariance geometry in RGB space to reduce this gap, allowing the existing fixed transform to capture more of the available redundancy without any modification to the transform itself.

---

## Originals

The unmodified Kodak Lossless True Color Image Suite (PCD0992) originals are included in `images/originals/` for direct comparison. The canonical source for the Kodak suite is:

> https://r0k.us/graphics/kodak/

These 24 images are an established benchmark in compression research, spanning a wide range of photographic content and inter-channel covariance geometries.

---

## File Structure

```
README.md
verify.sh
images/
    originals/          24 unmodified Kodak PCD0992 PNGs (768x512)
    clean/              24 SPDR source images (2560x1707 JPEG)
    fb1/                24 Facebook pipeline pass 1 outputs (2048x1366 JPEG)
    fb2/                24 Facebook pipeline pass 2 outputs (2048x1366 JPEG)
data/
    json/
        clean/          24 source image measurements
        fb1/            24 FB1 output measurements
        fb2/            24 FB2 output measurements
scripts/
    verify_suite.py     Full verification pipeline with comparison mode
    batch_measure.py    Standalone single-image/batch measurement tool
```

---

## Measurement Schema

Each JSON file contains:

| Field | Description |
|---|---|
| `source_file` | Filename |
| `format` | JPEG |
| `resolution` | Width x Height |
| `pixels` | Total pixel count |
| `file_size_bytes` | File size on disk |
| `bpp` | Bits per pixel (file_size x 8 / pixels) |
| `correlations` | Pairwise Pearson R-G, R-B, G-B and average absolute |
| `channel_stats` | Per-channel mean, std, min, max |
| `PC1_pct` / `PC2_pct` / `PC3_pct` | PCA variance explained |
| `eigenvalues` | Covariance eigenvalues |
| `condition_number` | lambda1 / lambda3 |
| `theta2` / `theta3` | BT.601 chrominance misalignment angles (degrees) |
| `loo_dev` | Leave-one-out deviation from theta2-theta3 regression |
| `spatial_autocorrelation_avg` | Mean lag-1 spatial autocorrelation |
| `sha256` | File hash for integrity verification |

---

## Series

| Paper | Repository |
|---|---|
| Statistical Characterization | [kodak-pcd0992-statistical-characterization](https://github.com/PearsonZero/kodak-pcd0992-statistical-characterization) |
| BT.601 Decorrelation Gap | [kodak-pcd0992-bt601-decorrelation-gap](https://github.com/PearsonZero/kodak-pcd0992-bt601-decorrelation-gap) |
| Geometry of Misalignment | [kodak-pcd0992-geometry-of-misalignment](https://github.com/PearsonZero/kodak-pcd0992-geometry-of-misalignment) |
| Orthogonal Constraint | [kodak-pcd0992-orthogonal-constraint](https://github.com/PearsonZero/kodak-pcd0992-orthogonal-constraint) |
| Directional Perturbation | [kodak-pcd0992-directional-perturbation-compression-response](https://github.com/PearsonZero/kodak-pcd0992-directional-perturbation-compression-response) |
| **Verification Suite** | **this repository** |

---

## References

Baetzel, J. (2026). SPDR Verification Suite: Independently Verifiable Compression Response Across the Kodak PCD0992 Suite. GitHub.

Kodak Lossless True Color Image Suite (PCD0992). Retrieved from https://r0k.us/graphics/kodak/
