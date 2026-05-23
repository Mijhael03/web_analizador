#!/usr/bin/env python3
"""
verificador_video.py
Verifica que existan videos en el directorio configurado.
Uso: python verificador_video.py
Retorna: exit 0 si hay videos, exit 1 si no.
"""

import sys
from pathlib import Path

VIDEOS_DIR = Path("/home/mijhael/Desktop/Tesis_cod/Videos_finales")
EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv"}


def main():
    if not VIDEOS_DIR.exists():
        print(f"ERROR: el directorio {VIDEOS_DIR} no existe.")
        sys.exit(1)

    videos = sorted([v for v in VIDEOS_DIR.iterdir() if v.suffix.lower() in EXTENSIONS])

    if not videos:
        print(f"ERROR: no se encontraron videos en {VIDEOS_DIR}")
        print("Formatos permitidos: .avi .mp4 .mov .mkv")
        sys.exit(1)

    print(f"OK: {len(videos)} video(s) encontrado(s):")
    for v in videos:
        print(f"  - {v.name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
