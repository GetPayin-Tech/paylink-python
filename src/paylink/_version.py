"""Single source of truth for the package version.

Sent on every request's ``User-Agent`` so server-side logs can attribute traffic
to a client version. Keep this in sync with ``[project].version`` in
``pyproject.toml`` (see CONTRIBUTING.md).
"""

__version__ = "0.2.0"
