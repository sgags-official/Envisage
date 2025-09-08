#!/usr/bin/env python3
"""
git_ops.py - small helper for add -> commit -> push (CLI)
Uses GitPython. This script expects an already-initialized git repo.
"""

import argparse
import os
from git import Repo, GitCommandError
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--message", required=True, help="Commit message")
    parser.add_argument("--all", action="store_true", help="git add --all")
    parser.add_argument("--remote", default=os.getenv("GIT_REMOTE", "origin"))
    parser.add_argument("--branch", default=os.getenv("GIT_BRANCH", "main"))
    args = parser.parse_args()

    try:
        repo = Repo(".", search_parent_directories=True)
    except Exception as e:
        print("Not a git repository (or Git not installed). Initialize a repo first.")
        return

    try:
        if args.all:
            repo.git.add(all=True)
        else:
            repo.git.add(".")
        repo.index.commit(args.message)
        origin = repo.remote(name=args.remote)
        print(f"Pushing to {args.remote}/{args.branch} ...")
        origin.push(refspec=f"{args.branch}:{args.branch}")
        print("Push complete.")
    except GitCommandError as e:
        print("Git failed:", e)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
