from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Each step is executed in a fresh Python process via os.execvpe after the previous
# step completes. This keeps memory use low on laptops/CI and avoids retaining
# pandas/scipy/reportlab objects across the full pipeline.
STEPS = [
    ("01 Generate synthetic source data", "generate_data", "generate_trial_data"),
    ("02 Build ADaM-style analysis datasets", "build_adam", "build_adam"),
    ("03 Generate TLFs", "generate_tlfs", "generate_tlfs"),
    ("04 Run validation checks", "qc_validation", "run_qc"),
    ("05 Render baseline reports", "render_reports", "render_all_reports"),
    ("06 Render professional reviewer package", "render_professional_package", "render_professional_package"),
    ("07 Render pharma-grade SAP and CSR-style report", "render_pharma_grade_documents", "render_pharma_grade_documents"),
]


def _prepare_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(HERE) + os.pathsep + env.get("PYTHONPATH", "")
    for key in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        env[key] = "1"
        os.environ[key] = "1"
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    os.chdir(ROOT)
    return env


def main() -> None:
    env = _prepare_env()
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if idx >= len(STEPS):
        print("\nPipeline complete. Review docs/, data/adam/, outputs/, metadata/, and qc/.")
        return

    label, module_name, func_name = STEPS[idx]
    print(f"\n=== {label} ===", flush=True)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    func()

    # Replace this Python process with the next step so memory is released.
    os.execvpe(sys.executable, [sys.executable, str(Path(__file__).resolve()), str(idx + 1)], env)


if __name__ == "__main__":
    main()
