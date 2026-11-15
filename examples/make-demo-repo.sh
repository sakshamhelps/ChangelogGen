#!/bin/sh
# Creates a small throw-away repo in ./demo-repo and prints its changelog.
set -e
rm -rf demo-repo && mkdir demo-repo && cd demo-repo
git init -q
git config user.name Demo && git config user.email demo@example.com
echo 1 > a && git add . && git commit -qm "feat: first feature"
git tag v0.1.0
echo 2 > b && git add . && git commit -qm "fix: handle empty input"
PYTHONPATH=../../src python3 -m changeloggen .
