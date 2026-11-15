import io, os, subprocess, tempfile, unittest, contextlib, shutil
import _path  # noqa
from changeloggen.cli import main
from changeloggen.gitlog import _git, GitError, build_releases
from changeloggen.render import classify
from changeloggen.gitlog import Commit

def run(argv):
    o, e = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
        try: c = main(argv)
        except SystemExit as x: c = x.code
    return c, o.getvalue(), e.getvalue()

def g(repo, *a, **kw):
    env = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@e.x", "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@e.x"}
    return subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True, env=env).stdout

@unittest.skipUnless(shutil.which("git"), "git not installed")
class T(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.d = t.name
        g(self.d, "init", "-q"); g(self.d, "config", "commit.gpgsign", "false"); g(self.d, "config", "tag.gpgsign", "false")
        self.n = 0
    def commit(self, msg):
        self.n += 1
        with open(os.path.join(self.d, f"f{self.n}"), "w") as f: f.write(str(self.n))
        g(self.d, "add", "."); g(self.d, "commit", "-q", "-m", msg)

    def test_full_flow_with_tags(self):
        self.commit("feat(api): add endpoint"); self.commit("fix: crash on empty input"); g(self.d, "tag", "v0.1.0")
        self.commit("chore: bump deps"); self.commit("feat!: drop python 3.8"); g(self.d, "tag", "-a", "v0.2.0", "-m", "second")
        self.commit("docs: update readme"); self.commit("random message")
        c, o, _ = run([self.d]); self.assertEqual(c, 0)
        self.assertLess(o.index("Unreleased"), o.index("v0.2.0")); self.assertLess(o.index("v0.2.0"), o.index("v0.1.0"))
        self.assertIn("**api:** add endpoint", o); self.assertIn("### Breaking Changes", o); self.assertIn("drop python 3.8", o)
        self.assertNotIn("bump deps", o); self.assertIn("random message", o)
        unreleased = o.split("## v0.2.0")[0]; self.assertIn("update readme", unreleased); self.assertNotIn("add endpoint", unreleased)
    def test_include_chore_since_and_no_unreleased(self):
        self.commit("feat: a"); g(self.d, "tag", "v1"); self.commit("chore: b"); g(self.d, "tag", "v2"); self.commit("fix: c")
        self.assertIn("b", run([self.d, "--include-chore"])[1])
        o = run([self.d, "--since", "v1", "--no-unreleased"])[1]; self.assertIn("v2", o); self.assertNotIn("## v1", o); self.assertNotIn("fix: c", o)
        self.assertEqual(run([self.d, "--since", "nope"])[0], 2)
    def test_history_not_modified(self):
        self.commit("feat: a"); g(self.d, "tag", "v1")
        before = (g(self.d, "log", "--format=%H"), g(self.d, "tag"), g(self.d, "status", "--porcelain"))
        run([self.d]); run([self.d, "-o", os.path.join(self.d, "CHANGELOG.md")])
        after = (g(self.d, "log", "--format=%H"), g(self.d, "tag"))
        self.assertEqual(before[:2], after)
    def test_write_guard_and_links(self):
        self.commit("fix: a"); out = os.path.join(tempfile.gettempdir(), "cl_test_out.md")
        if os.path.exists(out): os.remove(out)
        self.addCleanup(lambda: os.path.exists(out) and os.remove(out))
        self.assertEqual(run([self.d, "-o", out, "--repo-url", "https://github.com/o/r"])[0], 0)
        self.assertIn("https://github.com/o/r/commit/", open(out).read())
        self.assertEqual(run([self.d, "-o", out])[0], 2); self.assertEqual(run([self.d, "-o", out, "--force"])[0], 0)
    def test_no_hashes(self):
        self.commit("fix: a"); self.assertNotRegex(run([self.d, "--no-hashes"])[1], r"\([0-9a-f]{7}\)")
    def test_errors(self):
        with tempfile.TemporaryDirectory() as e:
            c, _, er = run([e]); self.assertEqual(c, 2); self.assertIn("not a Git repository", er)
        empty = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, empty); g(empty, "init", "-q")
        c, _, er = run([empty]); self.assertEqual(c, 2); self.assertIn("no commits", er)
        self.assertEqual(run([os.path.join(self.d, "missing")])[0], 2)
    def test_readonly_guard(self):
        for cmd in ("commit", "tag-d", "push", "reset", "checkout", "rebase"):
            with self.assertRaises(GitError): _git(self.d, cmd)
    def test_unicode_and_multiline_body(self):
        self.commit("feat: café ☕"); self.n += 1
        with open(os.path.join(self.d, "z"), "w") as f: f.write("z")
        g(self.d, "add", "."); g(self.d, "commit", "-q", "-m", "refactor: x", "-m", "BREAKING CHANGE: api removed")
        o = run([self.d])[1]; self.assertIn("café ☕", o); self.assertIn("Breaking Changes", o)
    def test_classify(self):
        self.assertIsNone(classify(Commit("a" * 40, "ci: x", "", "", ""))); self.assertEqual(classify(Commit("a", "Fix: Y", "", "", ""))[0], "fix")

if __name__ == "__main__": unittest.main()
