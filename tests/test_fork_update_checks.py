from pathlib import Path

from api import updates


def test_check_repo_can_compare_against_upstream_default_branch(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    calls = []

    def fake_git(args, cwd, timeout=10):
        calls.append(args)
        if args == ["fetch", "upstream", "--quiet"]:
            return "", True
        if args == ["symbolic-ref", "refs/remotes/upstream/HEAD"]:
            return "refs/remotes/upstream/master", True
        if args == ["rev-list", "--count", "HEAD..upstream/master"]:
            return "78", True
        if args == ["merge-base", "HEAD", "upstream/master"]:
            return "a" * 40, True
        if args == ["rev-parse", "--short", "a" * 40]:
            return "aaaaaaa", True
        if args == ["rev-parse", "--short", "upstream/master"]:
            return "bbbbbbb", True
        if args == ["remote", "get-url", "upstream"]:
            return "https://github.com/nesquena/hermes-webui.git", True
        if args == ["diff-index", "--quiet", "HEAD", "--"]:
            return "", True
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(updates, "_run_git", fake_git)

    info = updates._check_repo(
        tmp_path,
        "webui",
        check_remote="upstream",
    )

    assert info["behind"] == 78
    assert info["branch"] == "upstream/master"
    assert info["repo_url"] == "https://github.com/nesquena/hermes-webui"
    assert ["fetch", "origin", "--tags", "--force"] not in calls


def test_combined_update_check_uses_upstream_for_webui_and_agent(monkeypatch, tmp_path):
    calls = []
    webui_dir = tmp_path / "webui"
    agent_dir = tmp_path / "agent"

    def fake_check_repo(path, name, channel="stable", check_remote="origin"):
        calls.append((Path(path), name, channel, check_remote))
        return {"name": name, "behind": 0}

    monkeypatch.setattr(updates, "REPO_ROOT", webui_dir)
    monkeypatch.setattr(updates, "_AGENT_DIR", agent_dir)
    monkeypatch.setattr(updates, "_check_repo", fake_check_repo)

    updates.check_for_updates(force=True, include_agent=True, channel="stable")

    assert calls == [
        (webui_dir, "webui", "stable", "upstream"),
        (agent_dir, "agent", "stable", "upstream"),
    ]


def test_upstream_fetch_failure_is_unknown_not_up_to_date(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()

    def fake_git(args, cwd, timeout=10):
        if args == ["fetch", "upstream", "--quiet"]:
            return "network unavailable", False
        if args == ["diff-index", "--quiet", "HEAD", "--"]:
            return "", True
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(updates, "_run_git", fake_git)

    info = updates._check_repo(tmp_path, "webui", check_remote="upstream")

    assert info["behind"] is None
    assert info["stale_check"] is True
    assert info["error"] == "fetch failed: network unavailable"


def test_upstream_default_branch_falls_back_to_main(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    calls = []

    def fake_git(args, cwd, timeout=10):
        calls.append(args)
        if args == ["fetch", "upstream", "--quiet"]:
            return "", True
        if args == ["symbolic-ref", "refs/remotes/upstream/HEAD"]:
            return "", False
        if args == ["rev-parse", "--verify", "upstream/master"]:
            return "", False
        if args == ["rev-parse", "--verify", "upstream/main"]:
            return "a" * 40, True
        if args == ["rev-list", "--count", "HEAD..upstream/main"]:
            return "5", True
        if args == ["merge-base", "HEAD", "upstream/main"]:
            return "b" * 40, True
        if args == ["rev-parse", "--short", "b" * 40]:
            return "bbbbbbb", True
        if args == ["rev-parse", "--short", "upstream/main"]:
            return "aaaaaaa", True
        if args == ["remote", "get-url", "upstream"]:
            return "https://github.com/NousResearch/hermes-agent.git", True
        if args == ["diff-index", "--quiet", "HEAD", "--"]:
            return "", True
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(updates, "_run_git", fake_git)

    info = updates._check_repo(tmp_path, "agent", check_remote="upstream")

    assert info["behind"] == 5
    assert info["branch"] == "upstream/main"
    assert ["rev-parse", "--verify", "upstream/main"] in calls


def test_upstream_comparison_failure_is_unknown_not_up_to_date(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()

    def fake_git(args, cwd, timeout=10):
        if args == ["fetch", "upstream", "--quiet"]:
            return "", True
        if args == ["symbolic-ref", "refs/remotes/upstream/HEAD"]:
            return "refs/remotes/upstream/main", True
        if args == ["rev-list", "--count", "HEAD..upstream/main"]:
            return "fatal: bad revision 'HEAD..upstream/main'", False
        if args == ["diff-index", "--quiet", "HEAD", "--"]:
            return "", True
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(updates, "_run_git", fake_git)

    info = updates._check_repo(tmp_path, "agent", check_remote="upstream")

    assert info["behind"] is None
    assert info["stale_check"] is True
    assert info["error"] == "comparison failed: fatal: bad revision 'HEAD..upstream/main'"


def test_upstream_fetch_failure_redacts_credentials(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    token = "ghp_" + "A" * 36

    def fake_git(args, cwd, timeout=10):
        if args == ["fetch", "upstream", "--quiet"]:
            return f"fatal: https://user:{token}@github.com/private/repo.git", False
        if args == ["diff-index", "--quiet", "HEAD", "--"]:
            return "", True
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(updates, "_run_git", fake_git)

    info = updates._check_repo(tmp_path, "webui", check_remote="upstream")

    assert info["behind"] is None
    assert token not in info["error"]
    assert "<redacted>" in info["error"]


def test_origin_comparison_failure_is_unknown_when_fetch_is_skipped(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()

    def fake_git(args, cwd, timeout=10):
        if args == ["rev-parse", "--abbrev-ref", "@{upstream}"]:
            return "origin/prod", True
        if args == ["rev-list", "--count", "HEAD..origin/prod"]:
            return "fatal: bad revision 'HEAD..origin/prod'", False
        raise AssertionError(f"unexpected git args: {args!r}")

    monkeypatch.setattr(updates, "_run_git", fake_git)

    info = updates._check_repo_branch(tmp_path, "webui", fetch=False)

    assert info["behind"] is None
    assert info["branch"] == "origin/prod"
    assert info["stale_check"] is True
    assert info["error"] == "comparison failed: fatal: bad revision 'HEAD..origin/prod'"
