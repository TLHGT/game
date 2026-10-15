"""Genera un ejecutable de Windows de un solo archivo para cada versión del juego.

    python tools/build_exe.py            # dist/HospitalAbandonado.exe (el hospital)
    python tools/build_exe.py --aldea    # dist/AldeaDelVacio.exe (la Aldea del vacío)

Requiere `pip install pyinstaller`. Cada .exe solo empaqueta sus mapas y assets/:
el del hospital, hospital_*.json + elevators.json (arranca en la caverna); el de
la aldea, aldea.json (arranca en la entrada de la aldea). Los mazos editados se
guardan junto al .exe: decks_hospital.json o decks_aldea.json.
"""
import glob
import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS = {
    "hospital": dict(name="HospitalAbandonado", entry="main.py",
                     maps=["hospital_*.json", "elevators.json"]),
    "aldea": dict(name="AldeaDelVacio", entry="main_aldea.py", maps=["aldea.json"]),
}


def main():
    version = VERSIONS["aldea" if "--aldea" in sys.argv else "hospital"]
    maps = [m for pattern in version["maps"] for m in glob.glob(os.path.join(ROOT, "maps", pattern))]
    datas = [f"--add-data={m}{os.pathsep}maps" for m in maps]
    datas.append(f"--add-data={os.path.join(ROOT, 'assets')}{os.pathsep}assets")
    PyInstaller.__main__.run([
        os.path.join(ROOT, version["entry"]),
        f"--name={version['name']}",
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
    print(f"\nListo: {os.path.join(ROOT, 'dist', version['name'] + '.exe')}")


if __name__ == "__main__":
    sys.exit(main())
