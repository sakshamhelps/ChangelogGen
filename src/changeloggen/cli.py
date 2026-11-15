"""ChangelogGen: generate a changelog from local Git history and tags. Never modifies the repository."""
from __future__ import annotations
import argparse, os, sys
from . import __version__
from .gitlog import build_releases, GitError
from .render import render

def build_parser():
    p = argparse.ArgumentParser(prog="changeloggen",
        description="Generate a Markdown changelog from local Git commits and tags. Read-only: Git history is never modified.")
    p.add_argument("--version", action="version", version=f"changeloggen {__version__}")
    p.add_argument("repo", nargs="?", default=".", help="path to a Git repository (default: current directory)")
    p.add_argument("-o", "--output", help="write to this file (refuses to overwrite unless --force); default: stdout")
    p.add_argument("--force", action="store_true", help="allow overwriting the output file")
    p.add_argument("--title", default="Changelog")
    p.add_argument("--since", metavar="TAG", help="only include releases newer than TAG")
    p.add_argument("--no-unreleased", action="store_true", help="omit commits after the latest tag")
    p.add_argument("--include-chore", action="store_true", help="include chore/ci/build/test/style commits")
    p.add_argument("--repo-url", help="e.g. https://github.com/org/repo - turns commit hashes into links (text only; no network access)")
    p.add_argument("--no-hashes", action="store_true", help="omit commit hashes")
    return p

def _main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if not os.path.isdir(a.repo):
        print(f"changeloggen: error: not a directory: {a.repo}", file=sys.stderr); return 2
    if a.output and os.path.exists(a.output) and not a.force:
        print(f"changeloggen: error: {a.output} exists; use --force to overwrite", file=sys.stderr); return 2
    try:
        rels = build_releases(a.repo, a.since, not a.no_unreleased)
    except GitError as e:
        print(f"changeloggen: error: {e}", file=sys.stderr); return 2
    text = render(rels, a.title, a.repo_url, a.include_chore, not a.no_hashes)
    if a.output:
        try:
            with open(a.output, "w", encoding="utf-8", newline="\n") as f: f.write(text)
        except OSError as e:
            print(f"changeloggen: error: cannot write {a.output}: {e.strerror}", file=sys.stderr); return 2
    else:
        sys.stdout.write(text)
    return 0


def main(argv=None) -> int:
    """Entry point. Exits quietly if the output pipe is closed (e.g. `| head`)."""
    try:
        return _main(argv)
    except BrokenPipeError:
        try:
            sys.stdout = open(os.devnull, "w")
        except OSError:
            pass
        return 0
