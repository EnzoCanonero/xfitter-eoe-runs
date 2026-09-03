"""Checkout path handling shared by command-line adapters."""

import os
from pathlib import Path


REPO_ROOT_ENV = "XFITTER_EOE_REPO_ROOT"


def repository_root() -> Path:
    """Return the checkout root supplied by a repository launcher."""
    value = os.environ.get(REPO_ROOT_ENV)
    if not value:
        raise RuntimeError(
            f"{REPO_ROOT_ENV} is not set; use the corresponding command under scripts/"
        )
    return Path(value).expanduser().resolve()
