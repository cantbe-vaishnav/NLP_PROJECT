"""Command-line entry point for Phase 0 checks and run initialization."""

import argparse
import json
import platform

from safellm import __version__
from safellm.experiments import create_run, read_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check the installed Phase 0 package")
    init = commands.add_parser("init-run", help="Record metadata without training")
    init.add_argument("--config", required=True)
    init.add_argument("--output-root", required=True)
    args = parser.parse_args()
    if args.command == "doctor":
        import task_a
        import task_b
        import pipeline
        print(json.dumps({"safellm": __version__, "python": platform.python_version(),
                          "imports": "ok", "phase": 0}))
    else:
        print(create_run(read_config(args.config), args.output_root))


if __name__ == "__main__":
    main()
