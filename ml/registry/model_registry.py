"""
Model registry — tracks versions, integrity hashes, and metadata for all models.

Usage:
    python -m ml.registry.model_registry verify       # check SHA-256 hashes match
    python -m ml.registry.model_registry info         # print model metadata
    python -m ml.registry.model_registry bump <name>  # bump patch version
"""

import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MODEL_DIR = os.path.join(ROOT, "ml", "models")
REGISTRY_PATH = os.path.join(ROOT, "ml", "registry", "model_registry.json")


def _load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def _save_registry(registry: dict) -> None:
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify() -> bool:
    """Verify all model artifacts match their registered SHA-256 hashes."""
    registry = _load_registry()
    all_ok = True
    for name, meta in registry["models"].items():
        print(f"\n  Model: {name} (v{meta['version']})")
        for artifact, expected_hash in meta.get("sha256", {}).items():
            path = os.path.join(MODEL_DIR, artifact)
            if not os.path.exists(path):
                print(f"    MISSING  {artifact}")
                all_ok = False
                continue
            actual = sha256_file(path)
            if actual == expected_hash:
                print(f"    OK       {artifact}")
            else:
                print(f"    MISMATCH {artifact}")
                print(f"             expected: {expected_hash}")
                print(f"             actual:   {actual}")
                all_ok = False
    return all_ok


def info() -> None:
    """Print a summary of all registered models."""
    registry = _load_registry()
    print(f"Registry version: {registry['registry_version']}")
    for name, meta in registry["models"].items():
        print(f"\n  {name}")
        print(f"    Version:    {meta['version']}")
        print(f"    Algorithm:  {meta['algorithm']}")
        print(f"    Target:     {meta['target']}")
        print(f"    Features:   {meta['features']}")
        print(f"    Status:     {meta['status']}")
        metrics = meta.get("metrics", {})
        if metrics:
            print(f"    AUC-ROC:    {metrics.get('auc_roc', 'N/A')}")
            print(f"    Brier:      {metrics.get('brier_score', 'N/A')}")


def bump_version(model_name: str) -> None:
    """Bump the patch version of a model and update its hashes."""
    registry = _load_registry()
    if model_name not in registry["models"]:
        print(f"Unknown model: {model_name}")
        sys.exit(1)
    meta = registry["models"][model_name]
    parts = [int(x) for x in meta["version"].split(".")]
    parts[2] += 1
    meta["version"] = ".".join(str(p) for p in parts)
    # Refresh hashes
    for artifact in list(meta.get("sha256", {})):
        path = os.path.join(MODEL_DIR, artifact)
        if os.path.exists(path):
            meta["sha256"][artifact] = sha256_file(path)
    _save_registry(registry)
    print(f"  {model_name} → v{meta['version']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: model_registry.py <verify|info|bump> [model_name]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "verify":
        ok = verify()
        sys.exit(0 if ok else 1)
    elif cmd == "info":
        info()
    elif cmd == "bump" and len(sys.argv) >= 3:
        bump_version(sys.argv[2])
    else:
        print("Unknown command. Use verify, info, or bump.")
        sys.exit(1)
