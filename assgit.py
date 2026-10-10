#!/usr/bin/env python3
"""
minigit — a tiny Git-like version control system.

Supports: init, add, commit, log, branch, checkout, merge, push

Storage model (simplified but Git-inspired):
- Objects (blobs, trees, commits) are content-addressed by SHA-1 and
  zlib-compressed, stored under .minigit/objects/<sha[:2]>/<sha[2:]>
- A "tree" here is just a JSON dict of {path: blob_sha} (flat, no subdirs,
  to keep this readable — real Git trees are nested and binary-encoded).
- HEAD points at a ref (branch) or directly at a commit (detached).
- The index (staging area) is a JSON dict of {path: blob_sha}.
"""

import os
import sys
import hashlib
import zlib
import json
import time
import shutil
import difflib

MINIGIT_DIR = ".minigit"


# ---------------------------------------------------------------- storage --

def repo_path(*parts):
    return os.path.join(MINIGIT_DIR, *parts)


def hash_object(data: bytes, type_="blob") -> str:
    """Content-address and store an object, return its sha."""
    header = f"{type_} {len(data)}\0".encode()
    full = header + data
    sha = hashlib.sha1(full).hexdigest()
    path = repo_path("objects", sha[:2], sha[2:])
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(zlib.compress(full))
    return sha


def read_object(sha: str):
    """Return (type, data) for a stored object."""
    path = repo_path("objects", sha[:2], sha[2:])
    with open(path, "rb") as f:
        full = zlib.decompress(f.read())
    header, data = full.split(b"\0", 1)
    type_, _ = header.decode().split(" ")
    return type_, data


def read_blob_text(sha):
    if sha is None:
        return []
    _, data = read_object(sha)
    return data.decode().splitlines()


# ------------------------------------------------------------------- index --

def load_index():
    with open(repo_path("index")) as f:
        return json.load(f)


def save_index(index):
    with open(repo_path("index"), "w") as f:
        json.dump(index, f, indent=2, sort_keys=True)


def write_tree(index) -> str:
    tree_data = json.dumps(index, sort_keys=True).encode()
    return hash_object(tree_data, "tree")


# -------------------------------------------------------------------- HEAD --

def get_head_ref():
    """Return 'refs/heads/<name>' if HEAD is symbolic, else None (detached)."""
    with open(repo_path("HEAD")) as f:
        content = f.read().strip()
    if content.startswith("ref: "):
        return content[len("ref: "):]
    return None


def current_branch():
    ref = get_head_ref()
    return ref.split("/")[-1] if ref else None


def get_head_commit():
    ref = get_head_ref()
    if ref is None:
        with open(repo_path("HEAD")) as f:
            sha = f.read().strip()
        return sha or None
    ref_path = repo_path(ref)
    if not os.path.exists(ref_path):
        return None
    with open(ref_path) as f:
        return f.read().strip() or None


def set_head_commit(sha):
    ref = get_head_ref()
    if ref:
        ref_path = repo_path(ref)
        os.makedirs(os.path.dirname(ref_path), exist_ok=True)
        with open(ref_path, "w") as f:
            f.write(sha + "\n")
    else:
        with open(repo_path("HEAD"), "w") as f:
            f.write(sha + "\n")


def get_commit(sha):
    _, data = read_object(sha)
    return json.loads(data)


def get_tree_for_commit(sha):
    commit = get_commit(sha)
    _, tree_data = read_object(commit["tree"])
    return json.loads(tree_data)


# --------------------------------------------------------------- commands --

def init():
    if os.path.exists(MINIGIT_DIR):
        print("Already a minigit repository.")
        return
    os.makedirs(repo_path("objects"))
    os.makedirs(repo_path("refs", "heads"))
    with open(repo_path("HEAD"), "w") as f:
        f.write("ref: refs/heads/main\n")
    with open(repo_path("index"), "w") as f:
        json.dump({}, f)
    print("Initialized empty minigit repository in .minigit/")


def add(paths):
    if not paths:
        print("usage: minigit add <file> [file...]")
        return
    index = load_index()
    for path in paths:
        with open(path, "rb") as f:
            data = f.read()
        sha = hash_object(data, "blob")
        index[path] = sha
        print(f"added {path} -> {sha[:8]}")
    save_index(index)


def commit(message):
    index = load_index()
    if not index:
        print("nothing to commit (empty index)")
        return
    tree_sha = write_tree(index)
    parent = get_head_commit()
    commit_obj = {
        "tree": tree_sha,
        "parent": parent,
        "merge_parent": None,
        "message": message,
        "time": time.time(),
    }
    data = json.dumps(commit_obj, sort_keys=True).encode()
    sha = hash_object(data, "commit")
    set_head_commit(sha)
    branch = current_branch() or "HEAD"
    print(f"[{branch} {sha[:8]}] {message}")
    return sha


def log():
    sha = get_head_commit()
    if sha is None:
        print("no commits yet")
        return
    while sha:
        commit_obj = get_commit(sha)
        print(f"commit {sha}")
        if commit_obj.get("merge_parent"):
            print(f"Merge: {commit_obj['parent'][:8]} {commit_obj['merge_parent'][:8]}")
        print(f"Date:  {time.ctime(commit_obj['time'])}")
        print(f"\n    {commit_obj['message']}\n")
        sha = commit_obj["parent"]


def branch(name):
    sha = get_head_commit()
    if sha is None:
        print("cannot branch: no commits yet")
        return
    path = repo_path("refs", "heads", name)
    if os.path.exists(path):
        print(f"branch '{name}' already exists")
        return
    with open(path, "w") as f:
        f.write(sha + "\n")
    print(f"Created branch '{name}' at {sha[:8]}")


def checkout(name):
    ref_path = repo_path("refs", "heads", name)
    if not os.path.exists(ref_path):
        print(f"no such branch: {name}")
        return
    with open(repo_path("HEAD"), "w") as f:
        f.write(f"ref: refs/heads/{name}\n")

    sha = get_head_commit()
    if sha:
        tree = get_tree_for_commit(sha)
        for path, blob_sha in tree.items():
            _, data = read_object(blob_sha)
            with open(path, "wb") as f:
                f.write(data)
        save_index(tree)
    print(f"Switched to branch '{name}'")


def find_merge_base(sha1, sha2):
    def ancestors(sha):
        chain = []
        while sha:
            chain.append(sha)
            sha = get_commit(sha)["parent"]
        return chain

    a1 = ancestors(sha1)
    a2 = set(ancestors(sha2))
    for sha in a1:
        if sha in a2:
            return sha
    return None


def three_way_merge_file(base_lines, ours_lines, theirs_lines, path):
    """Return (merged_lines, had_conflict)."""
    if ours_lines == theirs_lines:
        return ours_lines, False
    if ours_lines == base_lines:
        return theirs_lines, False
    if theirs_lines == base_lines:
        return ours_lines, False

    # Real conflict: use difflib to try a line-level merge, falling back
    # to whole-file conflict markers if changes overlap.
    sm = difflib.SequenceMatcher(None, ours_lines, theirs_lines)
    merged = []
    conflict = False
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            merged.extend(ours_lines[i1:i2])
        else:
            conflict = True
            merged.append(f"<<<<<<< ours ({path})")
            merged.extend(ours_lines[i1:i2])
            merged.append("=======")
            merged.extend(theirs_lines[j1:j2])
            merged.append(">>>>>>> theirs")
    return merged, conflict


def merge(branch_name):
    ours_sha = get_head_commit()
    their_ref_path = repo_path("refs", "heads", branch_name)
    if not os.path.exists(their_ref_path):
        print(f"no such branch: {branch_name}")
        return
    with open(their_ref_path) as f:
        theirs_sha = f.read().strip()

    if ours_sha == theirs_sha:
        print("Already up to date.")
        return

    base_sha = find_merge_base(ours_sha, theirs_sha)
    base_tree = get_tree_for_commit(base_sha) if base_sha else {}
    ours_tree = get_tree_for_commit(ours_sha)
    theirs_tree = get_tree_for_commit(theirs_sha)

    merged_tree = dict(ours_tree)
    conflicted_paths = []

    all_paths = set(base_tree) | set(ours_tree) | set(theirs_tree)
    for path in sorted(all_paths):
        base_blob = base_tree.get(path)
        ours_blob = ours_tree.get(path)
        theirs_blob = theirs_tree.get(path)

        if ours_blob == theirs_blob:
            continue  # identical on both sides, nothing to do
        if base_blob == ours_blob:
            merged_tree[path] = theirs_blob  # only theirs changed it
            continue
        if base_blob == theirs_blob:
            continue  # only ours changed it, keep ours

        # Both sides changed this file: real three-way merge
        base_lines = read_blob_text(base_blob)
        ours_lines = read_blob_text(ours_blob)
        theirs_lines = read_blob_text(theirs_blob)

        merged_lines, had_conflict = three_way_merge_file(
            base_lines, ours_lines, theirs_lines, path
        )
        merged_data = ("\n".join(merged_lines) + "\n").encode()
        merged_sha = hash_object(merged_data, "blob")
        merged_tree[path] = merged_sha

        with open(path, "wb") as f:
            f.write(merged_data)

        if had_conflict:
            conflicted_paths.append(path)

    save_index(merged_tree)

    if conflicted_paths:
        # Stash the pending merge so `commit` can finish it later
        with open(repo_path("MERGE_HEAD"), "w") as f:
            f.write(theirs_sha + "\n")
        print("Auto-merging...")
        print("CONFLICT (content): Merge conflict in:")
        for p in conflicted_paths:
            print(f"    {p}")
        print("Fix conflicts in the files above, then run:")
        print(f'    minigit commit -m "Merge branch \'{branch_name}\'"')
        return

    # Clean merge: write files and create the merge commit directly
    for path, blob_sha in merged_tree.items():
        _, data = read_object(blob_sha)
        with open(path, "wb") as f:
            f.write(data)

    tree_sha = write_tree(merged_tree)
    commit_obj = {
        "tree": tree_sha,
        "parent": ours_sha,
        "merge_parent": theirs_sha,
        "message": f"Merge branch '{branch_name}'",
        "time": time.time(),
    }
    data = json.dumps(commit_obj, sort_keys=True).encode()
    sha = hash_object(data, "commit")
    set_head_commit(sha)
    print(f"Merge made commit {sha[:8]}")


def push(remote_path):
    """'Push' by copying objects and refs into another local .minigit-style dir."""
    os.makedirs(remote_path, exist_ok=True)
    remote_objects = os.path.join(remote_path, "objects")
    os.makedirs(remote_objects, exist_ok=True)

    local_objects = repo_path("objects")
    copied = 0
    for root, _, files in os.walk(local_objects):
        for fname in files:
            src = os.path.join(root, fname)
            rel = os.path.relpath(src, local_objects)
            dst = os.path.join(remote_objects, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst):
                shutil.copy(src, dst)
                copied += 1

    remote_refs = os.path.join(remote_path, "refs", "heads")
    os.makedirs(remote_refs, exist_ok=True)
    local_refs = repo_path("refs", "heads")
    for fname in os.listdir(local_refs):
        shutil.copy(os.path.join(local_refs, fname), os.path.join(remote_refs, fname))

    print(f"Pushed {copied} new object(s) and refs to {remote_path}")


# ---------------------------------------------------------------------- cli --

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd, rest = args[0], args[1:]

    if cmd == "init":
        init()
    elif cmd == "add":
        add(rest)
    elif cmd == "commit":
        if len(rest) >= 2 and rest[0] == "-m":
            commit(" ".join(rest[1:]))
        else:
            print('usage: minigit commit -m "message"')
    elif cmd == "log":
        log()
    elif cmd == "branch":
        if rest:
            branch(rest[0])
        else:
            print(f"* {current_branch()}")
    elif cmd == "checkout":
        if rest:
            checkout(rest[0])
        else:
            print("usage: minigit checkout <branch>")
    elif cmd == "merge":
        if rest:
            merge(rest[0])
        else:
            print("usage: minigit merge <branch>")
    elif cmd == "push":
        push(rest[0] if rest else "../remote-minigit")
    else:
        print(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()