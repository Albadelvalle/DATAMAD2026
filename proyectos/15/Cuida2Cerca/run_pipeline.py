"""Ejecuta todas las etapas de CuidaCerca de forma reproducible: python run_pipeline.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cuidacerca import coverage, forecast, preprocess, web_export  # noqa: E402

if __name__ == "__main__":
    preprocess.main()
    coverage.main()
    forecast.main()
    # La optimización es costosa y se ejecuta aparte: python -m cuidacerca.planes (y cuidacerca.experimentos)
    web_export.main()
