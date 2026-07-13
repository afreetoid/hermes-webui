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
