"""Command-line entry point: ``ineedvalidation lint | render | scaffold``."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from ineedvalidation import __version__, d2, evidence, nodes, views
from ineedvalidation.schema import HIERARCHY_TIERS

STUB = """---
id: {stub_id}
tier: ''
title: {case}
couples_to: []
cases:
- {case}
srqs: []
referent: ''
referent_status: none
validation_level: 0
---
# {case}

Stub written by ineedvalidation scaffold. Fill in the tier, the coupling, the
system response quantities and the referent, then delete this line.
"""


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
    for name in ("lint", "render", "scaffold"):
        command = sub.add_parser(name)
        command.add_argument(
            "hierarchy", help="directory holding nodes/, evidence/ and views/"
        )
        command.add_argument("--nodes", help="node notes directory")
        command.add_argument("--evidence", help="evidence files directory")
    lint = sub.choices["lint"]
    lint.add_argument("--library-map", help="file listing the known library names")
    render = sub.choices["render"]
    render.add_argument("--view", help="render only this named view")
    render.add_argument(
        "--all-views", action="store_true", help="render every view file as well"
    )
    render.add_argument("--root", help="render only this node and everything below it")
    render.add_argument("--views", help="view files directory")
    render.add_argument("--out", help="output directory")
    return parser


def _load(args):
    """Load the nodes, the evidence files and the merged summary."""
    root = Path(args.hierarchy)
    node_dir = Path(args.nodes) if args.nodes else root / "nodes"
    evidence_dir = Path(args.evidence) if args.evidence else root / "evidence"
    loaded = nodes.load(node_dir)
    files = evidence.load_dir(evidence_dir)
    return root, loaded, files, evidence.summarize(loaded, files)


def _lint(args):
    """Report every problem in the hierarchy."""
    _, loaded, files, summary = _load(args)
    library_text = Path(args.library_map).read_text() if args.library_map else None
    # Without a ledger there is nothing to lint the notes against, so the
    # two-way rules stay off and the declared fields carry the evidence.
    problems = nodes.lint(
        loaded,
        summary=summary if files else None,
        library_text=library_text,
        unfiled=evidence.unfiled_cases(loaded, files) if files else None,
    )
    for problem in problems:
        print("LINT:", problem)
    census = ", ".join(
        f"{tier}={sum(node.tier == tier for node in loaded.values())}"
        for tier in HIERARCHY_TIERS
    )
    print(f"{len(loaded)} nodes, {census}")
    return 1 if problems else 0


def _render(args):
    """Render one view, the two built-in views, or every view."""
    root, loaded, _, summary = _load(args)
    views_dir = Path(args.views) if args.views else root / "views"
    outdir = Path(args.out) if args.out else root / "output"
    names = [args.view] if args.view else list(views.builtin())
    if args.all_views:
        names = sorted(set(names) | set(views.load_dir(views_dir)))
    for name in names:
        try:
            view = views.resolve(name, views_dir)
        except KeyError as error:
            print(error.args[0], file=sys.stderr)
            return 2
        if args.root:
            view = replace(
                view,
                name=f"{name}_{args.root}",
                root=args.root,
                title=view.title or loaded[args.root].title,
            )
        selected = nodes.subtree(loaded, view.root) if view.root else loaded
        d2.render(selected, summary, view, outdir, views_dir)
        print("rendered", outdir / f"{view.name}.png")
    return 0


def _scaffold(args):
    """Write a stub note for every case no node owns."""
    root, loaded, files, _ = _load(args)
    node_dir = Path(args.nodes) if args.nodes else root / "nodes"
    written = 0
    for case, libraries in evidence.unfiled_cases(loaded, files).items():
        target = node_dir / f"unfiled-{case}.md"
        if target.exists():
            print("skipped, already present:", target)
            continue
        target.write_text(STUB.format(stub_id=f"unfiled-{case}", case=case))
        print("wrote", target, "for", ", ".join(libraries))
        written += 1
    print(f"{written} stub(s) written")
    return 0


def main(argv=None):
    """Run the command line."""
    args = build_parser().parse_args(argv)
    return {"lint": _lint, "render": _render, "scaffold": _scaffold}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
