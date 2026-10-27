# -*- coding: utf-8 -*-
"""
build_exe.py  –  Mete TODO en un solo .exe

Pon en la MISMA carpeta:
    RAM_Unlock_3DS.py     (el programa)
    build_exe.py          (este archivo)
    ctrtool.exe           (opcional, se incluye dentro del .exe)
    makerom.exe           (opcional, se incluye dentro del .exe)
    icon.ico              (opcional)

Luego ejecuta:   python build_exe.py
Resultado:       3DS_RAM_Unlock.exe  (un solo archivo, sin instalar nada)
"""
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "RAM_Unlock_3DS.py")
NAME = "3DS_RAM_Unlock"
STAGE = os.path.join(HERE, "_tools_stage")
BUILD = os.path.join(HERE, "_build")


def run(*cmd):
    print(">", " ".join(cmd))
    subprocess.check_call(list(cmd))


def find_tool(name):
    """Acepta 'ctrtool.exe' o nombres con prefijo (p.ej. 9a8976ba-ctrtool.exe)."""
    exact = os.path.join(HERE, name)
    if os.path.isfile(exact):
        return exact
    hits = sorted(glob.glob(os.path.join(HERE, "*" + name)))
    return hits[0] if hits else None


def main():
    if not os.path.isfile(MAIN):
        sys.exit("No encuentro RAM_Unlock_3DS.py junto a build_exe.py")
    if sys.platform != "win32":
        print("AVISO: no estás en Windows; el ejecutable resultante NO será un .exe de Windows.")

    print("== Instalando dependencias ==")
    run(sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller", "tkinterdnd2")

    # Copia las herramientas con nombre limpio para empaquetarlas
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE)
    add = []
    for tool in ("ctrtool.exe", "makerom.exe"):
        src = find_tool(tool)
        if src:
            shutil.copyfile(src, os.path.join(STAGE, tool))
            add += ["--add-data", f"{os.path.join(STAGE, tool)}{os.pathsep}tools"]
            print("Incluido:", os.path.basename(src))
        else:
            print("No encontrado (se omite):", tool)

    icon = os.path.join(HERE, "icon.ico")
    icon_args = ["--icon", icon] if os.path.isfile(icon) else []

    print("== Compilando ==")
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed", "--name", NAME,
        "--distpath", HERE, "--workpath", BUILD, "--specpath", BUILD,
        "--collect-all", "tkinterdnd2",
        *add, *icon_args, MAIN)

    shutil.rmtree(STAGE, ignore_errors=True)
    shutil.rmtree(BUILD, ignore_errors=True)

    exe = os.path.join(HERE, NAME + (".exe" if sys.platform == "win32" else ""))
    print("\nListo ->", exe)


if __name__ == "__main__":
    main()
