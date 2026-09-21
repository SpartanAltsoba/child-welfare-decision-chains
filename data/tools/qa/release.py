#!/usr/bin/env python3
"""Assemble a release: CHANGELOG.md section, version strings, MANIFEST.json.

Usage: python3 release.py <version> <notes.md> [--write]
  <notes.md>  the release's changelog section body (everything under the "## vX.Y.Z — date" heading),
              written by the maintainer for this release; the script adds the heading, the file count
              and root hash line, and places it above the previous sections.
Dry run prints what would change; --write applies it.
"""
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TODAY = datetime.date.today().isoformat()


def bump_versions(old, new, write):
    changes = []

    def sub(path, pattern, repl, count=0):
        p = os.path.join(ROOT, path)
        s = open(p).read()
        n, k = re.subn(pattern, repl, s, count=count, flags=re.M)
        if k:
            changes.append((path, pattern[:40], k))
            if write:
                open(p, "w").write(n)

    o = re.escape(old)
    sub("README.md", rf"version-{o}-blue", f"version-{new}-blue")
    sub("README.md", rf"releases/tag/v{o}", f"releases/tag/v{new}")
    sub("README.md", rf"\*\*v{o} release:\*\*", f"**v{new} release:**")
    sub("README.md", rf"\(Version {o}\)", f"(Version {new})")
    sub("README.md", rf"The current release is \*\*v{o}\*\*", f"The current release is **v{new}**")
    sub("CITATION.cff", rf'^version: "{o}"', f'version: "{new}"')
    sub("CITATION.cff", rf"\(v{o}\)", f"(v{new})")
    sub("CITATION.cff", r"^date-released: .*$", f'date-released: "{TODAY}"')
    sub("PROVENANCE.md", rf"\| Version \(current release\) \| v{o} \|", f"| Version (current release) | v{new} |")
    sub("PROVENANCE.md", rf"Cite the version \(`v{o}`\)", f"Cite the version (`v{new}`)")
    return changes


def main():
    version, notes_path = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    os.chdir(ROOT)
    old_manifest = json.load(open("MANIFEST.json"))
    old_version = old_manifest["dataset_version"]
    # 1. manifest
    out = subprocess.run([sys.executable, "data/tools/qa/build_manifest.py", version] + (["--write"] if write else []), capture_output=True, text=True).stdout
    print(out.strip())
    m = re.search(r"(\d+) files, root_hash ([0-9a-f]{64})", out)
    count, root = int(m.group(1)), m.group(2)
    # 2. changelog: new section on top of the existing file
    body = open(notes_path).read().strip()
    section = f"## v{version} — {TODAY}\n\n{body}\n\nFiles: {count:,}. Root hash `{root}`.\n"
    cl = open("CHANGELOG.md").read()
    if f"## v{version} " in cl:
        cl = re.sub(rf"## v{re.escape(version)} .*?(?=\n## v)", section, cl, count=1, flags=re.S)
    else:
        i = cl.index("\n## v")
        cl = cl[:i] + "\n" + section + cl[i:]
    if write:
        open("CHANGELOG.md", "w").write(cl)
    print(f"CHANGELOG.md: v{version} section {len(section.splitlines())} lines ({'written' if write else 'dry run'})")
    # 3. version strings
    for path, pat, k in bump_versions(old_version, version, write):
        print(f"  {path}: {k} × {pat}")
    p = os.path.join(ROOT, "README.md"); s = open(p).read()
    s2 = re.sub(r"\d{1,3},\d{3} files · SHA-256", f"{count:,} files · SHA-256", s)
    if write and s2 != s: open(p, "w").write(s2)
    # 4. provenance root hash line
    p = os.path.join(ROOT, "PROVENANCE.md"); s = open(p).read()
    line = f"v{version} root_hash: {root}   (data/tools/qa/build_manifest.py)"
    if f"v{version} root_hash" in s:
        s2 = re.sub(rf"v{re.escape(version)} root_hash: [0-9a-f]{{64}}[^\n]*", line, s)
    else:
        s2 = re.sub(rf"(v{re.escape(old_version)} root_hash: [0-9a-f]{{64}}[^\n]*)", rf"\1\n{line}", s, count=1)
    if write and s2 != s: open(p, "w").write(s2)
    print("PROVENANCE.md: root hash line", "written" if write else "dry run")


if __name__ == "__main__":
    main()
