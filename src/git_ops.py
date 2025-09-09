#!/usr/bin/env python3
"""
git_ops.py - modular git helpers for Day 2

Provides git_add_commit_push(repo_dir, message, all=True, remote=None, branch=None)
Handles:
 - no changes (no-op)
 - initial commit
 - push errors (attempt fetch+pull/rebase then re-push)
 - network errors reported to caller
"""

import os
import logging
import time
from git import Repo, GitCommandError, InvalidGitRepositoryError
from dotenv import load_dotenv

load_dotenv()

LOG = logging.getLogger("envisage.git")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
LOG.addHandler(ch)

DEFAULT_REMOTE = os.getenv("GIT_REMOTE", "origin")
DEFAULT_BRANCH = os.getenv("GIT_BRANCH", "main")


class GitOpsResult:
    def __init__(self, ok: bool, message: str):
        self.ok = ok
        self.message = message

    def __repr__(self):
        return f"<GitOpsResult ok={self.ok} message={self.message!r}>"


def git_add_commit_push(repo_dir: str | None, message: str,
                        all_files: bool = True,
                        remote: str | None = None,
                        branch: str | None = None,
                        retry_on_rejected: bool = True) -> GitOpsResult:
    remote = remote or DEFAULT_REMOTE
    branch = branch or DEFAULT_BRANCH
    repo_dir = repo_dir or "."

    try:
        repo = Repo(repo_dir, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return GitOpsResult(False, "Not a git repository. Initialize one with `git init`.")
    except Exception as e:
        return GitOpsResult(False, f"Failed to open repo: {e}")

    # Detect changes (staged or unstaged or untracked)
    try:
        has_untracked = bool(repo.untracked_files)
        is_dirty = repo.is_dirty(untracked_files=True)
    except Exception:
        has_untracked = False
        is_dirty = False

    if not is_dirty and not has_untracked:
        return GitOpsResult(False, "No changes to commit (clean working tree).")

    try:
        # Stage
        if all_files:
            repo.git.add(all=True)
        else:
            repo.git.add(".")
    except GitCommandError as e:
        LOG.exception("git add failed")
        return GitOpsResult(False, f"git add failed: {e}")

    # Commit
    try:
        # If HEAD doesn't exist (initial commit), commit anyway
        repo.index.commit(message)
    except Exception as e:
        LOG.exception("git commit failed")
        return GitOpsResult(False, f"git commit failed: {e}")

    # Push (with simple retry/pull-on-reject logic)
    try:
        if not repo.remotes:
            return GitOpsResult(False, "No remotes configured; cannot push. Configure a remote named 'origin' or set GIT_REMOTE.")
        origin = repo.remote(name=remote)
        LOG.info(f"Pushing to {remote}/{branch} ...")
        push_info = origin.push(refspec=f"{branch}:{branch}")
        # push_info is a list of PushInfo objects, inspect first
        if push_info:
            info = push_info[0]
            if info.flags & info.ERROR:
                raise GitCommandError(f"Push error: {info.summary}", 1)
        return GitOpsResult(True, "Push complete.")
    except GitCommandError as e:
        LOG.warning("Push failed: %s", e)
        if retry_on_rejected:
            # Try fetch + pull (rebase) then push again
            try:
                LOG.info("Attempting fetch + pull --rebase and retry push...")
                origin.fetch()
                # try to rebase local changes on top of remote branch
                try:
                    repo.git.pull(remote, branch, "--rebase")
                except GitCommandError:
                    # fallback to plain pull merge if rebase fails
                    repo.git.pull(remote, branch)
                # push again
                origin.push(refspec=f"{branch}:{branch}")
                return GitOpsResult(True, "Push complete after pull/rebase.")
            except Exception as e2:
                LOG.exception("Push still failed after pull/rebase")
                return GitOpsResult(False, f"Push failed after pull: {e2}")
        return GitOpsResult(False, f"Push failed: {e}")
    except Exception as e:
        LOG.exception("Unexpected error during push")
        return GitOpsResult(False, f"Push failed: {e}")
