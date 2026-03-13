"""Run the 3D cricket prototype (Panda3D version).

Install:
    python -m pip install -r requirements_3d.txt
Run:
    python main_3d.py
"""
import sys


def main() -> int:
    try:
        from game3d.panda_app import Cricket3DPandaApp
    except ModuleNotFoundError as exc:
        if exc.name == "direct" or exc.name == "panda3d":
            print("ERROR: Panda3D is not installed for this Python interpreter.")
            print(f"Run: {sys.executable} -m pip install -r requirements_3d.txt")
            return 1
        raise

    app = Cricket3DPandaApp()
    app.run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
