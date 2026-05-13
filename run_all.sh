#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="programs/python:${PYTHONPATH:-}"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

echo "=== 01 Generate synthetic source data ==="
python programs/python/generate_data.py

echo "=== 02 Build ADaM-style analysis datasets ==="
python programs/python/build_adam.py

echo "=== 03 Generate TLFs ==="
python programs/python/generate_tlfs.py

echo "=== 04 Run validation checks ==="
python programs/python/qc_validation.py

echo "=== 05 Render baseline reports ==="
python programs/python/render_reports.py

echo "=== 06 Render professional reviewer package ==="
python programs/python/render_professional_package.py

echo "=== 07 Render pharma-grade SAP and CSR-style report ==="
python programs/python/render_pharma_grade_documents.py

echo "Pipeline complete. Review docs/, data/adam/, outputs/, metadata/, and qc/."
