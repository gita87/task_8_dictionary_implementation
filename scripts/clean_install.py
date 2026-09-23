"""Gate wheel and sdist installations in fresh virtualenvs outside the checkout."""

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--wheelhouse", type=Path, help="Offline dependency wheel directory")
args = parser.parse_args()
artifacts = sorted((root / "dist").glob("qaos_dictionary-*.whl"))
sdists = sorted((root / "dist").glob("qaos_dictionary-*.tar.gz"))
if len(artifacts) != 1 or len(sdists) != 1:
    raise SystemExit("dist must contain exactly one dictionary wheel and one sdist")
clean_env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
with tempfile.TemporaryDirectory(prefix="dictionary-install-") as directory:
    base = Path(directory)
    for index, artifact in enumerate([*artifacts, *sdists]):
        environment = base / str(index)
        venv.EnvBuilder(with_pip=True).create(environment)
        binary = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        command = [str(binary), "-m", "pip", "install", "--find-links", str(root / "vendor")]
        if args.wheelhouse:
            command += ["--no-index", "--find-links", str(args.wheelhouse.resolve())]
        subprocess.run([*command, str(artifact)], cwd=base, env=clean_env, check=True)
        subprocess.run(
            [str(binary), "-I", str(root / "scripts/installed_smoke.py")],
            cwd=base,
            env=clean_env,
            check=True,
        )
        subprocess.run([*command, f"{artifact}[ui]"], cwd=base, env=clean_env, check=True)
        subprocess.run(
            [str(binary), "-I", str(root / "scripts/installed_smoke.py"), "--ui"],
            cwd=base,
            env=clean_env,
            check=True,
        )
        subprocess.run([str(binary), "-m", "pip", "check"], cwd=base, env=clean_env, check=True)
        subprocess.run(
            [str(binary), "-I", "-m", "cli", "--help"], cwd=base, env=clean_env, check=True
        )
        entry = environment / (
            "Scripts/qaos-dictionary.exe" if os.name == "nt" else "bin/qaos-dictionary"
        )
        subprocess.run([str(entry), "--help"], cwd=base, env=clean_env, check=True)
