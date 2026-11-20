"""The ``parse-bench`` CLI with this project's registrations loaded (``python -m idp.parse_cli ...``)."""

import sys

import idp.parse_pipelines  # noqa: F401  (registers our pipelines)
from parse_bench.cli import main

if __name__ == "__main__":
    sys.exit(main())
