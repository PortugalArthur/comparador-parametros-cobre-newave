from pathlib import Path
import unittest

from infraestrutura.preparar_ambiente import garantir_dependencias

garantir_dependencias({"pyarrow": "pyarrow>=14", "duckdb": "duckdb>=1.0"})
suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), top_level_dir=str(Path(__file__).resolve().parents[1]))
resultado = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not resultado.wasSuccessful())
