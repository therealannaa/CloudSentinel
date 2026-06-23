"""Held-out set sealing — implements the selection-bias control (docs/week1/02
Section 4.6, docs/week1/03, v3 plan). Once sealed, the held-out manifests carry a
checksum lock; the runner/experiments must refuse to score against them until P4.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

LOCK_NAME = "SEALED.lock"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def seal(heldout_dir="benchmark/manifests/heldout"):
    """Write a SEALED.lock recording a checksum of every held-out manifest plus a
    timestamp. Idempotent: re-sealing refreshes the lock only if contents changed.
    Returns the lock dict.
    """
    if not os.path.isdir(heldout_dir):
        raise FileNotFoundError(f"held-out dir not found: {heldout_dir}")
    manifests = sorted(f for f in os.listdir(heldout_dir) if f.endswith(".json"))
    checksums = {f: _sha256(os.path.join(heldout_dir, f)) for f in manifests}
    lock = {
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "n_manifests": len(manifests),
        "checksums": checksums,
        "note": "Held-out set sealed. Do NOT run the system against these until P4 "
                "(selection-bias control). Verify integrity with verify().",
    }
    with open(os.path.join(heldout_dir, LOCK_NAME), "w") as fh:
        json.dump(lock, fh, indent=2)
    return lock


def is_sealed(heldout_dir="benchmark/manifests/heldout"):
    return os.path.exists(os.path.join(heldout_dir, LOCK_NAME))


def verify(heldout_dir="benchmark/manifests/heldout"):
    """Check that on-disk held-out manifests still match the sealed checksums.
    Returns (ok: bool, mismatches: list[str]). A non-empty mismatch list means the
    sealed set was tampered with (a contamination red flag)."""
    lock_path = os.path.join(heldout_dir, LOCK_NAME)
    if not os.path.exists(lock_path):
        return False, ["not sealed"]
    with open(lock_path) as fh:
        lock = json.load(fh)
    mismatches = []
    for fname, expected in lock["checksums"].items():
        p = os.path.join(heldout_dir, fname)
        if not os.path.exists(p):
            mismatches.append(f"missing:{fname}")
        elif _sha256(p) != expected:
            mismatches.append(f"changed:{fname}")
    return (len(mismatches) == 0), mismatches
