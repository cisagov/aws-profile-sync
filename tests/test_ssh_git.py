"""Exercise the Git profile handler using isolated local repositories."""

# Standard Python Libraries
import shutil
import subprocess  # nosec B404: Local Git fixture commands only.

# Third-Party Libraries
import pytest

# cisagov Libraries
from aws_profile_sync.handlers.ssh_git import SSHGitHandler


@pytest.mark.parametrize(
    "repo_name", ["roles", "team.roles", "team.git.roles", "roles.git"]
)
def test_fetch_repository_name(tmp_path, monkeypatch, repo_name):
    """Preserve dots in repository names during both clone and cached fetch."""
    git = shutil.which("git")
    assert git is not None
    source = tmp_path / "source" / f"{repo_name}.git"
    source.mkdir(parents=True)
    # Scope configuration to the test, avoiding user hooks, signing and remotes.
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "empty-gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    url = f"ssh://git@profiles.example.test/{repo_name}.git"
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.{source.as_uri()}.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", url)

    def run_git(*args):
        # The executable is resolved above; all arguments are test constants.
        return subprocess.run(  # nosec B603
            [git, *args], cwd=source, check=True, capture_output=True, text=True
        )

    run_git("init", "--initial-branch=master")
    run_git("config", "user.name", "Repository Test")
    run_git("config", "user.email", "repository-test@example.test")
    run_git("config", "commit.gpgsign", "false")
    run_git("config", "core.hooksPath", str(tmp_path / "no-hooks"))
    roles = source / "roles"
    roles.write_text("[example]\nregion = us-east-1\n", encoding="utf-8")
    run_git("add", "roles")
    run_git("commit", "-m", "Initial test profiles")

    handler = SSHGitHandler(tmp_path / "cache")
    assert handler.can_handle(url)
    assert "".join(handler.fetch(url)) == roles.read_text(encoding="utf-8")
    clone = handler.work_path / repo_name
    assert (clone / ".git").is_dir()

    # Exercise the cached checkout after the local source advances.
    roles.write_text("[example]\nregion = eu-west-2\n", encoding="utf-8")
    run_git("add", "roles")
    run_git("commit", "-m", "Update test profiles")
    assert "".join(handler.fetch(url)) == roles.read_text(encoding="utf-8")
    assert sorted(p.name for p in handler.work_path.iterdir()) == [repo_name]
