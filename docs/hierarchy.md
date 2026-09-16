# The hierarchy

A validation hierarchy is a set of notes, one per case, arranged in levels from the
complete system down to unit problems. The notes are the curated part: which cases
exist, what they couple to, which response quantities matter, and what the referent
is. Everything a test can testify to is computed from the evidence files instead of
being typed by hand.

## Layout

```
hierarchy/
  nodes/       one Markdown note per node, with YAML frontmatter
  evidence/    one JSON file per repository, written by pytest
  views/       named views (.yaml) and hand-edited overrides (.d2)
  output/      generated .gen.d2, .svg and .png
```

Every directory can be pointed elsewhere with a flag. Only `nodes/` is required.

## A node note

```yaml
---
id: benchmark-bench
level: benchmark
title: Bench loop closure
couples_to:
- subsystem-mixer
cases:
- bench-loop
srqs:
- loop residual
referent: bench loop data
referent_status: in-hand
validation_level: 2
domain_overlap:
  covers:
  - loop-bandwidth
  - actuator-count
  misses:
  - residual-amplitude
---
```

`level` is one of `complete`, `system`, `subsystem`, `benchmark` or `unit`, and a node's
id must start with it, so the identifier states the level rather than encoding it.
`couples_to` names the nodes one level up that this node feeds. `cases` is the join key:
every slug listed here collects the tests that declare it. `referent_status` is one of
`none`, `identified`, `requested` or `in-hand`. `validation_level` is the
NASA-STD-7009B Table 9 level claimed for the node, from 0 to 4.

`domain_overlap` names the axes of the real system's domain of operation that the
referent covers, and the axes it does not. A referent rarely overlaps the system on
every axis, so a level-2 claim rests on the covered axes and says so; the uncovered
axes are the ones a reader of the ledger has to discount. Recording both lists is what
keeps "within the domain of operation" from becoming a matter of opinion.

A node may also carry `libraries_planned` for work that is intended but not yet
tested. Once tests exist, the libraries shown on the figure are computed from them.

## Linting

```console
$ ineedvalidation lint hierarchy/
```

The structural rules check that a note's file name matches its identifier, that the
identifier starts with the node's own level, that every `couples_to` target exists and
sits at a higher level, that every node below the complete level has at least one edge,
and that the referent status and validation level are in range. A level of 2 or above
needs a referent in hand, validation evidence, and a `domain_overlap` naming the axes
the referent covers; a level of 3 or above is only meaningful at the complete level,
because those levels describe measurements on the real system. No axis may appear in
both halves of a `domain_overlap`.

When evidence files are present the lint also runs in the other direction: a case
named by a test must belong to some node, a node that declares cases must have at
least one test, a response quantity named by a test must be one the node lists, a seam
must join two coupled nodes, and a claimed validation level of 2 or above needs a passing validation test that actually passed, not merely one that was marked. Without any evidence file
these rules stay off, since there is nothing to check the notes against.

`ineedvalidation scaffold hierarchy/` writes a stub note for every case a test names
that no node owns. The stub leaves the level blank so that the curator has to place it
deliberately. An existing note is never overwritten.

## Rendering

```console
$ ineedvalidation render hierarchy/
$ ineedvalidation render hierarchy/ --root subsystem-mixer
$ ineedvalidation render hierarchy/ --view optics-branch
$ ineedvalidation render hierarchy/ --all-views
```

Rendering needs two external binaries: `d2` version 0.7 or later for the layout, and
`rsvg-convert` for the raster output. Both are checked before anything is written, and
a missing one is reported by name.

The layout is deterministic. There is one row per level, node sizes are uniform, and an
invisible chain of anchors pins each node to the rank of its level, but only where its
real edges would otherwise let it drift. The level labels are written into the SVG at
the left margin afterwards, since the layout engine has no place for them.

Two views are built in. `reference` is the plain black on white drawing of the
structure. `status` is the dark figure that adds the libraries and the evidence kinds
to each label, fills each node by its validation level, colours its outline by its
referent status, and draws the legend. Evidence that passed is shown plainly and
evidence that was only claimed is shown in parentheses.

## Named views and overrides

A view is a small YAML file in `views/`:

```yaml
name: optics-branch
root: subsystem-mixer
mode: status
layout: elk
show: [libraries, evidence]
highlight: [mylib]
title: Optics branch
```

`highlight` dims everything that does not involve the named libraries. `show` chooses
what goes into the node labels.

Rendering a view writes `output/<name>.gen.d2`. For a figure that has to look right in
a talk, put a file at `views/<name>.d2` that imports the generated one and redefines
what it needs:

```text
...@"../output/optics-branch.gen.d2"

benchmark-bench: { label: "Bench loop\nclosure (2026 data)" }
subsystem-mixer.style.stroke: "#ffffff"
```

Quote the import path: `d2` replaces everything after the last dot with `.d2`, so an
unquoted `.gen` would be read as the extension. When the override exists it is
compiled instead of the generated file, which keeps regenerating safe. Overrides are
keyed by node identifier, so they survive a regeneration. Last-mile edits in a vector
editor are disposable and are not tracked.
