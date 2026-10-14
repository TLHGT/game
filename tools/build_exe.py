"""Genera dist/HospitalAbandonado.exe: el juego del hospital en un solo archivo.

    python tools/build_exe.py

Requiere `pip install pyinstaller`. Solo empaqueta los mapas del hospital
(hospital_*.json + elevators.json) y assets/; el .exe arranca en la caverna.
Los mazos editados se guardan en decks_hospital.json junto al .exe.
"""
import glob
import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "HospitalAbandonado"


def main():
    maps = glob.glob(os.path.join(ROOT, "maps", "hospital_*.json"))
    maps.append(os.path.join(ROOT, "maps", "elevators.json"))
    datas = [f"--add-data={m}{os.pathsep}maps" for m in maps]
    datas.append(f"--add-data={os.path.join(ROOT, 'assets')}{os.pathsep}assets")
    PyInstaller.__main__.run([
        os.path.join(ROOT, "main.py"),
        f"--name={NAME}",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--paths={ROOT}",
        f"--distpath={os.path.join(ROOT, 'dist')}",
        f"--workpath={os.path.join(ROOT, 'build')}",
        f"--specpath={os.path.join(ROOT, 'build')}",
        "--hidden-import=game.game",
        "--collect-submodules=combate",
        *datas,
    ])
    print(f"\nListo: {os.path.join(ROOT, 'dist', NAME + '.exe')}")


if __name__ == "__main__":
    sys.exit(main())
