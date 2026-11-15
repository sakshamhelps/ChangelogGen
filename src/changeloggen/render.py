"""Group commits (Conventional Commits aware) and render Keep-a-Changelog style Markdown."""
from __future__ import annotations
import re
from .gitlog import Release, Commit

CC = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
SECTIONS = [("breaking", "Breaking Changes"), ("feat", "Added"), ("fix", "Fixed"), ("perf", "Performance"),
            ("refactor", "Changed"), ("docs", "Documentation"), ("other", "Other")]
TYPE_TO_SECTION = {"feat": "feat", "feature": "feat", "fix": "fix", "bugfix": "fix", "perf": "perf", "refactor": "refactor",
                   "docs": "docs", "doc": "docs"}
HIDDEN_TYPES = {"chore", "ci", "build", "test", "tests", "style"}

def classify(c: Commit):
    """Return (section_key, text) or None to hide."""
    m = CC.match(c.subject)
    breaking = "BREAKING CHANGE" in c.body or "BREAKING-CHANGE" in c.body
    if m:
        t = m["type"].lower(); desc = m["desc"].strip()
        if m["scope"]: desc = f"**{m['scope']}:** {desc}"
        if m["bang"] or breaking: return "breaking", desc
        if t in HIDDEN_TYPES: return None
        return TYPE_TO_SECTION.get(t, "other"), desc
    return ("breaking" if breaking else "other"), c.subject

def render(releases: list[Release], title="Changelog", repo_url: str | None = None, show_hidden=False, short_sha=True) -> str:
    lines = [f"# {title}", "", "Generated from Git history by ChangelogGen.", ""]
    if not releases:
        lines.append("_No releases or commits found._")
    for rel in releases:
        head = f"## [{rel.name}]" if rel.name == "Unreleased" else f"## {rel.name}"
        if rel.date: head += f" - {rel.date}"
        lines += [head, ""]
        buckets: dict[str, list[str]] = {k: [] for k, _ in SECTIONS}
        for c in rel.commits:
            res = classify(c)
            if res is None and show_hidden: res = ("other", c.subject)
            if res is None: continue
            key, text = res
            ref = f" ({c.sha[:7]})" if short_sha else ""
            if repo_url and short_sha: ref = f" ([{c.sha[:7]}]({repo_url.rstrip('/')}/commit/{c.sha}))"
            buckets[key].append(f"- {text}{ref}")
        any_ = False
        for key, label in SECTIONS:
            if buckets[key]:
                any_ = True; lines += [f"### {label}", "", *buckets[key], ""]
        if not any_: lines += ["_No user-facing changes._", ""]
    return "\n".join(lines).rstrip() + "\n"
