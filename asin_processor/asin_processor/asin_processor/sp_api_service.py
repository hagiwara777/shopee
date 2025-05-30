"""
Wrapper so that scripts executed *inside asin_processor/*
can still do:

    from sp_api_service import ...

and resolve to the real module that lives in the repo root.
"""
import sys, pathlib, importlib

root = pathlib.Path(__file__).resolve().parent.parent  # /workspaces/shopee
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# 実体をインポートし、この名前で再公開
_real = importlib.import_module("sp_api_service")
globals().update(_real.__dict__)
