#!/bin/bash
# verify.sh — One-command verification for SPDR suite
# Usage: ./verify.sh
#
# Measures all images and compares against published JSON data.
# Requires: Python 3.8+, NumPy, Pillow
#   pip install numpy Pillow

set -e

echo ""
echo "============================================================"
echo "  SPDR Verification Suite — Baetzel (2026)"
echo "  Kodak PCD0992 Lossless True Color Image Suite"
echo "============================================================"
echo ""

# Check dependencies
if ! python3 -c "import numpy, PIL" 2>/dev/null; then
    echo "  Installing dependencies..."
    pip install numpy Pillow --quiet
    echo ""
fi

# Run verification with comparison against published data
python3 scripts/verify_suite.py \
    --clean images/clean \
    --fb1 images/fb1 \
    --fb2 images/fb2 \
    --output verification_output \
    --compare data/json/clean data/json/fb1 data/json/fb2
