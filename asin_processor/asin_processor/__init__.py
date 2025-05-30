# --- ensure repo root is on PYTHONPATH ---
import sys, pathlib
root_dir = pathlib.Path(__file__).resolve().parent.parent   # /workspaces/shopee
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
# -----------------------------------------
