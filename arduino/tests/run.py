import json
import math
from pathlib import Path
import subprocess
import sys


def test(executable, vectors, client):
    fit = vectors["fit"]
    maturity = client["maturityUsed"]
    fkz = next(f["fkz"] for f in vectors["fkz"] if f["day"] == client["referenceDay"])
    fc = (fit["a"] + fit["b"] * math.log(maturity)) * fkz
    lines = [f'{fit["a"]} {fit["b"]} {fit["r2"]} {fit["n"]} {maturity} {fc}']
    for factor in vectors["fkz"]:
        lines.append(f'{factor["day"]} {factor["fkz"]}')
    for row in vectors["rows"]:
        lines.append(
            f'{row["day"]:.3f} {row["timeH"]} {row["temp"]:.5f} '
            f'{row["fc"]:.5f} {row["m"]} {row["fcComputed"]}'
        )
    subprocess.run([executable], input="\n".join(lines), text=True, check=True)


if __name__ == "__main__":
    vectors_path = Path(__file__).with_name("reference-vectors.json")
    vectors = json.loads(vectors_path.read_bytes())
    for name in ("fullPrecision", "previewRounded"):
        print(name, flush=True)
        test(Path(sys.argv[1]).resolve(), vectors[name], vectors["clientPrediction"])
