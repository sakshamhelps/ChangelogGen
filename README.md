# ChangelogGen

Generate a readable Markdown changelog from your **local** Git history and tags. Commits are grouped by release (tag) and by type, with first-class support for [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `feat!:`, `BREAKING CHANGE:`). ChangelogGen is read-only: it never modifies Git history, tags or the working tree, and makes no network requests.

## Requirements

- Python 3.10+
- Git installed and on `PATH` (ChangelogGen runs the `git` command locally)

## Install

```
pip install .
# or: PYTHONPATH=src python -m changeloggen --help
```

## Usage

```
changeloggen [REPO] [-o FILE [--force]] [--title T] [--since TAG] [--no-unreleased]
             [--include-chore] [--repo-url URL] [--no-hashes]
```

```
$ changeloggen                          # print changelog for the current repo
$ changeloggen ../myrepo -o CHANGELOG.md
$ changeloggen --since v1.2.0 --repo-url https://github.com/org/repo
```

- Releases are the repository's tags (ordered by date); commits after the newest tag appear under **Unreleased**.
- Merge commits are skipped. `chore`, `ci`, `build`, `test` and `style` commits are hidden unless `--include-chore`.
- Non-conventional commit subjects are kept under **Other**.
- `--repo-url` only formats text links to commits; nothing is fetched.
- `-o` refuses to overwrite an existing file unless `--force` is given.

Internally only the Git subcommands `log`, `tag`/`for-each-ref` and `rev-parse` are ever invoked; any other subcommand is refused in code (and covered by a test).

Exit codes: `0` success, `2` error (not a repo, no commits, git missing, unknown tag, I/O error).

## Limitations

- Quality depends on commit messages; the tool does not rewrite or judge them.
- Tag order follows tag creation date, not semantic-version order.
- Release dates are commit dates of the tagged commit.
- The output is a starting point: review before publishing.

## Tests

```
python -m unittest discover -s tests -v
```

Tests create throw-away Git repositories in temporary directories and need `git`.

## Licence

MIT, Copyright (c) 2026 BYREX. No third-party dependencies.

The MIT licence covers the code only. The BYREX name and branding are not licensed for use by forks: see [TRADEMARK.md](TRADEMARK.md).
