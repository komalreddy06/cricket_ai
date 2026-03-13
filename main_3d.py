"""Run the 3D prototype.

Use the SAME Python interpreter for install + run:
    python -m pip install -r requirements_3d.txt
    python main_3d.py
"""
import sys


def main() -> int:
    try:
        from game3d.app import Cricket3DApp
    except ModuleNotFoundError as exc:
        if exc.name == "ursina":
            print("ERROR: Ursina is not installed for this Python interpreter.")
            print(f"Run: {sys.executable} -m pip install -r requirements_3d.txt")
            return 1
        raise

    Cricket3DApp().run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
