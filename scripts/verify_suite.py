#!/usr/bin/env python3
"""
verify_suite.py — Independent Verification Script
===================================================
Baetzel (2026) | Kodak PCD0992 SPDR Verification Suite

Measures all images in the repository and produces:
  1. One JSON per image (matching published schema)
  2. A summary CSV comparing SPDR sources → FB pipeline outputs
  3. A markdown summary table for quick inspection

Usage:
    python3 verify_suite.py

    By default, looks for images in:
        images/clean/       (24 SPDR source images)
        images/fb1/         (24 FB pipeline pass 1 outputs)
        images/fb2/         (24 FB pipeline pass 2 outputs)

    Output written to:
        verification_output/json/clean/
        verification_output/json/fb1/
        verification_output/json/fb2/
        verification_output/summary.csv
        verification_output/summary.md

    To verify against published JSONs:
        python3 verify_suite.py --compare data/json/clean data/json/fb1 data/json/fb2

Dependencies:
    Python 3.8+, NumPy, Pillow
    pip install numpy Pillow
"""

import sys, os, json, hashlib, csv, argparse
import numpy as np
from PIL import Image


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}


def measure_image(filepath):
    """Measure a single image. Returns dict matching published JSON schema."""
    img = Image.open(filepath).convert('RGB')
    pixels = np.array(img, dtype=np.float64)
    h, w, _ = pixels.shape

    R = pixels[:, :, 0].flatten()
    G = pixels[:, :, 1].flatten()
    B = pixels[:, :, 2].flatten()

    n_pixels = h * w
    file_size = os.path.getsize(filepath)
    bpp = round((file_size * 8) / n_pixels, 3)

    # Pairwise Pearson correlations
    rg = np.corrcoef(R, G)[0, 1]
    rb = np.corrcoef(R, B)[0, 1]
    gb = np.corrcoef(G, B)[0, 1]
    avg_abs_r = round((abs(rg) + abs(rb) + abs(gb)) / 3, 4)

    # Covariance → PCA
    data = np.vstack([R, G, B])
    cov = np.cov(data)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    total_var = np.sum(eigenvalues)
    pc_pcts = [round(e / total_var * 100, 2) for e in eigenvalues]

    condition_number = round(eigenvalues[0] / eigenvalues[2], 2) if eigenvalues[2] > 0 else float('inf')

    # BT.601 misalignment angles
    bt601_Cb = np.array([-0.169, -0.331, 0.500])
    bt601_Cr = np.array([0.500, -0.419, -0.081])

    def angle_between(v1, v2):
        cos_a = np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1, 1)
        return np.degrees(np.arccos(abs(cos_a)))

    theta2 = round(angle_between(eigenvectors[:, 1], bt601_Cb), 2)
    theta3 = round(angle_between(eigenvectors[:, 2], bt601_Cr), 2)

    # LOO deviation from θ₂–θ₃ regression (Paper 5 orthogonal constraint)
    predicted_theta3 = 1.004 * theta2 - 2.372
    loo_dev = round(theta3 - predicted_theta3, 2)

    # Spatial autocorrelation (lag-1, H+V average, per channel)
    def spatial_autocorr_channel(ch_2d):
        h_corr = np.corrcoef(ch_2d[:, :-1].flatten(), ch_2d[:, 1:].flatten())[0, 1]
        v_corr = np.corrcoef(ch_2d[:-1, :].flatten(), ch_2d[1:, :].flatten())[0, 1]
        return (h_corr + v_corr) / 2

    sa_avg = round(np.mean([spatial_autocorr_channel(pixels[:, :, c]) for c in range(3)]), 6)

    # SHA-256
    with open(filepath, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()

    # Channel statistics
    ch_stats = {}
    for name, ch in [('R', R), ('G', G), ('B', B)]:
        ch_stats[name] = {
            'mean': round(float(np.mean(ch)), 4),
            'std': round(float(np.std(ch)), 4),
            'min': int(np.min(ch)),
            'max': int(np.max(ch))
        }

    fmt = os.path.splitext(filepath)[1].upper().replace('.', '')
    if fmt == 'JPG':
        fmt = 'JPEG'

    return {
        'source_file': os.path.basename(filepath),
        'format': fmt,
        'resolution': f'{w}x{h}',
        'pixels': n_pixels,
        'file_size_bytes': file_size,
        'bpp': bpp,
        'correlations': {
            'R_G': round(rg, 6),
            'R_B': round(rb, 6),
            'G_B': round(gb, 6),
            'avg_abs_r': avg_abs_r
        },
        'channel_stats': ch_stats,
        'PC1_pct': pc_pcts[0],
        'PC2_pct': pc_pcts[1],
        'PC3_pct': pc_pcts[2],
        'eigenvalues': {
            'PC1': round(eigenvalues[0], 4),
            'PC2': round(eigenvalues[1], 4),
            'PC3': round(eigenvalues[2], 4)
        },
        'condition_number': condition_number,
        'theta2': theta2,
        'theta3': theta3,
        'loo_dev': loo_dev,
        'spatial_autocorrelation_avg': sa_avg,
        'sha256': sha
    }


def process_directory(image_dir, output_dir):
    """Measure all images in a directory, write JSONs, return list of results."""
    if not os.path.isdir(image_dir):
        print(f"  Directory not found: {image_dir}")
        return []

    files = sorted([
        f for f in os.listdir(image_dir)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        and not f.startswith('._')
    ])

    if not files:
        print(f"  No images found in {image_dir}")
        return []

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for i, fname in enumerate(files, 1):
        filepath = os.path.join(image_dir, fname)
        try:
            result = measure_image(filepath)
            out_name = os.path.splitext(fname)[0] + '.json'
            out_path = os.path.join(output_dir, out_name)
            with open(out_path, 'w') as f:
                json.dump(result, f, indent=2)

            c = result['correlations']
            print(f"  [{i:>2}/{len(files)}] {fname:<35s} Avg|r|={c['avg_abs_r']:.4f}  BPP={result['bpp']:.3f}  ✓")
            results.append(result)

        except Exception as e:
            print(f"  [{i:>2}/{len(files)}] {fname:<35s} ERROR: {e}")

    return results


def extract_kodim_number(filename):
    """Extract KODIM number from filename for sorting and matching."""
    name = filename.upper()
    for i in range(1, 25):
        if f'KODIM{i:02d}' in name:
            return i
    return 99


def generate_summary(clean_results, fb1_results, fb2_results, output_dir):
    """Generate CSV and markdown summary tables."""

    # Index results by KODIM number
    def index_by_kodim(results):
        indexed = {}
        for r in results:
            num = extract_kodim_number(r['source_file'])
            indexed[num] = r
        return indexed

    clean = index_by_kodim(clean_results)
    fb1 = index_by_kodim(fb1_results)
    fb2 = index_by_kodim(fb2_results)

    all_nums = sorted(set(list(clean.keys()) + list(fb1.keys()) + list(fb2.keys())))

    # CSV
    csv_path = os.path.join(output_dir, 'summary.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Image',
            'Clean_BPP', 'Clean_AvgR', 'Clean_PC1', 'Clean_Cond', 'Clean_KB',
            'FB1_BPP', 'FB1_AvgR', 'FB1_PC1', 'FB1_Cond', 'FB1_KB',
            'FB2_BPP', 'FB2_AvgR', 'FB2_PC1', 'FB2_Cond', 'FB2_KB',
            'BPP_Reduction_FB1_pct'
        ])
        for num in all_nums:
            c = clean.get(num, {})
            f1 = fb1.get(num, {})
            f2 = fb2.get(num, {})

            c_bpp = c.get('bpp', '')
            f1_bpp = f1.get('bpp', '')

            reduction = ''
            if c_bpp and f1_bpp:
                reduction = round((1 - f1_bpp / c_bpp) * 100, 1)

            writer.writerow([
                f'kodim{num:02d}',
                c.get('bpp', ''),
                c.get('correlations', {}).get('avg_abs_r', ''),
                c.get('PC1_pct', ''),
                c.get('condition_number', ''),
                round(c.get('file_size_bytes', 0) / 1024, 1) if c else '',
                f1.get('bpp', ''),
                f1.get('correlations', {}).get('avg_abs_r', ''),
                f1.get('PC1_pct', ''),
                f1.get('condition_number', ''),
                round(f1.get('file_size_bytes', 0) / 1024, 1) if f1 else '',
                f2.get('bpp', ''),
                f2.get('correlations', {}).get('avg_abs_r', ''),
                f2.get('PC1_pct', ''),
                f2.get('condition_number', ''),
                round(f2.get('file_size_bytes', 0) / 1024, 1) if f2 else '',
                reduction
            ])

    # Markdown
    md_path = os.path.join(output_dir, 'summary.md')
    with open(md_path, 'w') as f:
        f.write('# Verification Summary\n\n')
        f.write('Generated by `verify_suite.py` — Baetzel (2026)\n\n')

        # Source images table
        f.write('## SPDR Source Images (2560×1707)\n\n')
        f.write('| Image | BPP | Avg \\|r\\| | PC1% | Cond | Size (KB) |\n')
        f.write('|-------|-----|-----------|------|------|-----------|\n')
        for num in all_nums:
            c = clean.get(num, {})
            if c:
                f.write(f"| kodim{num:02d} | {c['bpp']:.3f} | {c['correlations']['avg_abs_r']:.4f} | {c['PC1_pct']:.2f} | {c['condition_number']:.1f} | {c['file_size_bytes']/1024:.1f} |\n")

        # FB pipeline table
        f.write('\n## Facebook Pipeline Output (2048×1366)\n\n')
        f.write('| Image | FB1 BPP | FB2 BPP | Avg \\|r\\| | PC1% | BPP Reduction |\n')
        f.write('|-------|---------|---------|-----------|------|---------------|\n')
        for num in all_nums:
            f1 = fb1.get(num, {})
            f2 = fb2.get(num, {})
            c = clean.get(num, {})
            if f1:
                reduction = ''
                if c and c.get('bpp'):
                    reduction = f"{(1 - f1['bpp'] / c['bpp']) * 100:.1f}%"
                f2_bpp = f"{f2['bpp']:.3f}" if f2 else '—'
                f.write(f"| kodim{num:02d} | {f1['bpp']:.3f} | {f2_bpp} | {f1['correlations']['avg_abs_r']:.4f} | {f1['PC1_pct']:.2f} | {reduction} |\n")

        # Suite averages
        if fb1_results and clean_results:
            avg_clean_bpp = np.mean([r['bpp'] for r in clean_results])
            avg_fb1_bpp = np.mean([r['bpp'] for r in fb1_results])
            avg_reduction = (1 - avg_fb1_bpp / avg_clean_bpp) * 100
            avg_clean_r = np.mean([r['correlations']['avg_abs_r'] for r in clean_results])
            avg_fb1_r = np.mean([r['correlations']['avg_abs_r'] for r in fb1_results])

            f.write(f'\n## Suite Averages\n\n')
            f.write(f'| Metric | SPDR Source | FB1 Output |\n')
            f.write(f'|--------|-------------|------------|\n')
            f.write(f'| Mean BPP | {avg_clean_bpp:.3f} | {avg_fb1_bpp:.3f} |\n')
            f.write(f'| Mean Avg \\|r\\| | {avg_clean_r:.4f} | {avg_fb1_r:.4f} |\n')
            f.write(f'| Mean BPP Reduction | — | {avg_reduction:.1f}% |\n')

    print(f"\n  Summary CSV:      {csv_path}")
    print(f"  Summary Markdown: {md_path}")


def compare_jsons(generated_dir, published_dir):
    """Compare generated JSONs against published JSONs for verification."""
    if not os.path.isdir(published_dir):
        return

    gen_files = {f for f in os.listdir(generated_dir) if f.endswith('.json')}
    pub_files = {f for f in os.listdir(published_dir) if f.endswith('.json') and not f.startswith('._')}

    common = gen_files & pub_files
    if not common:
        print(f"  No matching JSON files to compare between {generated_dir} and {published_dir}")
        return

    print(f"\n  Comparing {len(common)} JSONs: generated vs published")
    mismatches = 0

    for fname in sorted(common):
        with open(os.path.join(generated_dir, fname)) as f:
            gen = json.load(f)
        with open(os.path.join(published_dir, fname)) as f:
            pub = json.load(f)

        diffs = []
        for key in ['bpp', 'PC1_pct', 'PC2_pct', 'PC3_pct', 'condition_number']:
            if key in gen and key in pub:
                if gen[key] != pub[key]:
                    diffs.append(f"{key}: {gen[key]} vs {pub[key]}")

        if 'correlations' in gen and 'correlations' in pub:
            for ck in ['R_G', 'R_B', 'G_B', 'avg_abs_r']:
                gv = gen['correlations'].get(ck)
                pv = pub['correlations'].get(ck)
                if gv is not None and pv is not None and gv != pv:
                    diffs.append(f"corr.{ck}: {gv} vs {pv}")

        if 'sha256' in gen and 'sha256' in pub:
            if gen['sha256'] != pub['sha256']:
                diffs.append("SHA256 MISMATCH")

        if diffs:
            print(f"  ⚠  {fname}: {'; '.join(diffs)}")
            mismatches += 1
        else:
            print(f"  ✓  {fname}")

    if mismatches == 0:
        print(f"\n  All {len(common)} JSONs match published values.")
    else:
        print(f"\n  {mismatches}/{len(common)} files had differences.")


def main():
    parser = argparse.ArgumentParser(
        description='Verify SPDR suite images and compare to published measurements.'
    )
    parser.add_argument('--clean', default='images/clean',
                        help='Directory of SPDR source images (default: images/clean)')
    parser.add_argument('--fb1', default='images/fb1',
                        help='Directory of FB pass 1 images (default: images/fb1)')
    parser.add_argument('--fb2', default='images/fb2',
                        help='Directory of FB pass 2 images (default: images/fb2)')
    parser.add_argument('--output', default='verification_output',
                        help='Output directory (default: verification_output)')
    parser.add_argument('--compare', nargs=3, metavar=('PUB_CLEAN', 'PUB_FB1', 'PUB_FB2'),
                        help='Compare generated JSONs against published JSON directories')

    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  Baetzel (2026) — SPDR Verification Suite")
    print(f"{'='*60}")

    # Process each directory
    print(f"\n  Processing SPDR source images: {args.clean}")
    clean_out = os.path.join(args.output, 'json', 'clean')
    clean_results = process_directory(args.clean, clean_out)

    print(f"\n  Processing FB pass 1: {args.fb1}")
    fb1_out = os.path.join(args.output, 'json', 'fb1')
    fb1_results = process_directory(args.fb1, fb1_out)

    print(f"\n  Processing FB pass 2: {args.fb2}")
    fb2_out = os.path.join(args.output, 'json', 'fb2')
    fb2_results = process_directory(args.fb2, fb2_out)

    # Generate summary
    if clean_results or fb1_results or fb2_results:
        print(f"\n  Generating summary tables...")
        generate_summary(clean_results, fb1_results, fb2_results, args.output)

    # Optional comparison against published JSONs
    if args.compare:
        pub_clean, pub_fb1, pub_fb2 = args.compare
        print(f"\n{'='*60}")
        print(f"  Comparing against published JSONs")
        print(f"{'='*60}")
        if clean_results:
            compare_jsons(clean_out, pub_clean)
        if fb1_results:
            compare_jsons(fb1_out, pub_fb1)
        if fb2_results:
            compare_jsons(fb2_out, pub_fb2)

    print(f"\n{'='*60}")
    print(f"  Done. Output: {args.output}/")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
