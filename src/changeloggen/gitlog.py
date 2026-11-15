"""Read-only access to a local Git repository. Only `git log`, `git tag`, `git rev-parse` are ever run."""
from __future__ import annotations
import subprocess
from dataclasses import dataclass

class GitError(Exception):
    pass

ALLOWED = {"log", "tag", "rev-parse", "for-each-ref"}

def _git(repo: str, *args: str) -> str:
    if args[0] not in ALLOWED:
        raise GitError(f"refusing to run git {args[0]}: ChangelogGen is read-only")
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise GitError("git executable not found; install Git and make sure it is on PATH")
    except NotADirectoryError:
        raise GitError(f"not a directory: {repo}")
    except PermissionError:
        raise GitError(f"permission denied: {repo}")
    if r.returncode != 0:
        msg = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else f"git {args[0]} failed"
        raise GitError(msg)
    return r.stdout

@dataclass
class Commit:
    sha: str
    subject: str
    body: str
    author: str
    date: str

@dataclass
class Release:
    name: str          # tag name, or "Unreleased"
    date: str | None
    commits: list[Commit]

SEP, FIELD = "\x1e", "\x1f"

def is_repo(repo: str) -> bool:
    try:
        return _git(repo, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except GitError:
        return False

def has_commits(repo: str) -> bool:
    try:
        _git(repo, "rev-parse", "--verify", "HEAD"); return True
    except GitError:
        return False

def list_tags(repo: str) -> list[tuple[str, str]]:
    """Return [(tag, date)] sorted by commit date ascending. Handles annotated tags via the commit they point at."""
    out = _git(repo, "for-each-ref", "--sort=creatordate", "--format=%(refname:short)\x1f%(*committerdate:short)\x1f%(committerdate:short)", "refs/tags")
    tags = []
    for line in out.splitlines():
        if not line.strip(): continue
        name, peeled, plain = (line.split(FIELD) + ["", ""])[:3]
        tags.append((name, peeled or plain))
    return tags

def commits_in(repo: str, rev_range: str) -> list[Commit]:
    fmt = FIELD.join(["%H", "%s", "%b", "%an", "%cs"]) + SEP
    out = _git(repo, "log", "--no-merges", f"--pretty=format:{fmt}", rev_range)
    commits = []
    for rec in out.split(SEP):
        rec = rec.strip("\n")
        if not rec.strip(): continue
        sha, subj, body, author, date = (rec.split(FIELD) + [""] * 5)[:5]
        commits.append(Commit(sha, subj.strip(), body.strip(), author, date))
    return commits

def build_releases(repo: str, since: str | None = None, include_unreleased: bool = True) -> list[Release]:
    if not is_repo(repo): raise GitError(f"not a Git repository: {repo}")
    if not has_commits(repo): raise GitError("repository has no commits yet")
    tags = list_tags(repo)
    releases: list[Release] = []
    prev = None
    for name, date in tags:
        rng = f"{prev}..{name}" if prev else name
        releases.append(Release(name, date, commits_in(repo, rng))); prev = name
    if include_unreleased:
        rng = f"{prev}..HEAD" if prev else "HEAD"
        un = commits_in(repo, rng)
        if un: releases.append(Release("Unreleased", None, un))
    releases.reverse()  # newest first
    if since:
        names = [r.name for r in releases]
        if since not in names: raise GitError(f"tag not found: {since}")
        releases = releases[: names.index(since)]  # releases strictly newer than `since`
    return releases
