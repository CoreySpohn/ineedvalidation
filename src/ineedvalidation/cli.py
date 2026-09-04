"""Command-line entry point: ``ineedvalidation lint | render | scaffold``."""

import argparse
import sys

from ineedvalidation import __version__

COMMANDS = ("lint", "render", "scaffold")


def build_parser():
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ineedvalidation",
        description=(
            "Lint and render a validation hierarchy from node notes and test evidence."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        p = sub.add_parser(name)
        p.add_argument(
            "hierarchy", help="directory holding nodes/, evidence/ and views/"
        )
    return parser


def main(argv=None):
    """Run the command line."""
    args = build_parser().parse_args(argv)
    print(f"ineedvalidation {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
