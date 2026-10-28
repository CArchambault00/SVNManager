"""Cyra release automation for SVN Manager (patch_generation).

Rules (decided with the Cyra installer gate):
  * Selected files under cyra/ mean the change ships a new Cyra release.
  * cyra/ files are committed to SVN and packaged under CyraReleases only.
    They are never recorded in the Web/DB patch (no FOLDER row for cyra).
  * cyra/ + webpage/ or Database/ files -> a patch is created from web/db
    only AND a Cyra release is built; the release is linked to that new patch.
  * cyra/ only (no webpage/Database/)   -> no patch; a Cyra release is
    built and linked to the patch the PREVIOUS Cyra release was linked to
    (customers then need nothing new before installing it).
  * No cyra/ files                      -> patch only, as before.

"Linked" = DEV_TOOL.CYRA_RELEASE.REQUIRES_PATCH(_NAME), written here at
generation time (the Cyra Releases page remains a manual fallback). The
gate file cyra-depends.json is written into the built release (folder +
zip) so it travels to the customer with the release, like depend.txt
travels with a patch.

The release version is the next minor version after the latest one in the
CyraReleases SVN (1.1.0 -> 1.2.0), unless cyra/VERSION is already ahead.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import zipfile

from svn_operations import run_svn

ROOT_MARKERS = ("cyra/", "webpage/", "Database/")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_FILES = ("cyra/VERSION", "cyra/core/__init__.py")
RELEASES_REL = "CyraReleases"


# ---------------------------------------------------------------------------
# Classification / version math (pure, unit-tested)
# ---------------------------------------------------------------------------

def normalize_rel(path):
    """WC-relative path with the classification root first.

    Selected paths may carry a scope prefix (e.g. 'jtdev/cyra/...' when the
    profile svn_path is a subfolder); strip everything before the earliest
    known root segment.

    Earliest marker wins so cyra/webpage/... and cyra/database/... stay under
    cyra/ (never reclassified as webpage/Database for the Web/DB patch).
    """
    rel = str(path).replace("\\", "/").lstrip("/")
    best_idx = None
    for marker in ROOT_MARKERS:
        idx = rel.find(marker)
        if idx >= 0 and (best_idx is None or idx < best_idx):
            best_idx = idx
    if best_idx is not None and best_idx > 0:
        return rel[best_idx:]
    return rel


def is_cyra_path(path):
    """True when the path is under the cyra/ tree (after scope strip)."""
    return normalize_rel(path).startswith("cyra/")


def classify_files(selected_files):
    """Split selected files into cyra / web / db / other buckets."""
    groups = {"cyra": [], "web": [], "db": [], "other": []}
    for f in selected_files or []:
        rel = normalize_rel(f)
        if rel.startswith("cyra/"):
            groups["cyra"].append(f)
        elif rel.startswith("webpage/"):
            groups["web"].append(f)
        elif rel.startswith("Database/"):
            groups["db"].append(f)
        else:
            groups["other"].append(f)
    return groups


def files_for_patch_package(selected_files):
    """Paths that belong in the Web/DB patch package (excludes cyra/).

    Cyra sources commit with the selection and ship via CyraReleases; they
    must not hit FOLDER/PATCH_DETAIL or the patch folder copy.
    """
    return [f for f in (selected_files or []) if not is_cyra_path(f)]


def parse_semver(text):
    m = SEMVER_RE.match(str(text or "").strip())
    if not m:
        return None
    return tuple(int(g) for g in m.groups())


def next_minor(version_tuple):
    return (version_tuple[0], version_tuple[1] + 1, 0)


def format_semver(version_tuple):
    return ".".join(str(n) for n in version_tuple)


def pick_release_version(released_versions, source_version):
    """Next minor after the latest released, or the source version if ahead."""
    released = [v for v in (parse_semver(r) for r in released_versions or []) if v]
    source = parse_semver(source_version)
    if not released:
        return format_semver(source) if source else "1.0.0"
    latest = max(released)
    if source and source > latest:
        return format_semver(source)
    return format_semver(next_minor(latest))


def pick_previous_link(links, before_version):
    """Highest linked release strictly below before_version, or None.

    links: iterable of dicts with VERSION / REQUIRES_PATCH / REQUIRES_PATCH_NAME
    (DEV_TOOL.CYRA_RELEASE rows, or the same keys parsed from a gate file).
    """
    before = parse_semver(before_version)
    best = None
    for link in links or []:
        ver = parse_semver(link.get("VERSION"))
        patch = link.get("REQUIRES_PATCH")
        if ver is None or patch in (None, ""):
            continue
        if before is not None and ver >= before:
            continue
        if best is None or ver > parse_semver(best["VERSION"]):
            best = link
    return best


PATCH_NAME_RE = re.compile(r"S?(\d+)\.(\d+)\.(\d+)")


def parse_patch_name(patch_name):
    """'S1.0.1085-W1S1' -> (1, 0, 1085); 'S2.0.0001-W0' -> (2, 0, 1)."""
    if not patch_name:
        return None
    m = PATCH_NAME_RE.search(str(patch_name))
    return tuple(int(g) for g in m.groups()) if m else None


def patch_key(version_tuple):
    """Sortable NUMBER(6) key: major*100000 + minor*10000 + revision.

    Patch revisions cap at 9999 and major/minor are single digit, so
    S2.0.0001 = 200001 correctly outranks S1.0.9999 = 109999. A bare
    revision number would break at the S2 rollover.
    """
    if version_tuple is None:
        return None
    major, minor, revision = version_tuple
    return major * 100000 + minor * 10000 + revision


def resolve_patch_key(patch_number, patch_name):
    """Full composite key from the patch name when possible.

    Falls back to the stored number, upgraded from legacy revision-only
    values (< 10000, written before the encoding existed) via the name.
    """
    key = patch_key(parse_patch_name(patch_name))
    if key is not None:
        return key
    return int(patch_number) if patch_number not in (None, "") else None


def gate_file_json(version, patch_number, patch_name):
    """Deterministic cyra-depends.json content (no timestamp: stable in SVN).

    requiresPatch is the composite patch_key; requiresPatchVersion is the
    human '1.0.1085' form the installer gate compares as a tuple.
    """
    key = resolve_patch_key(patch_number, patch_name)
    parsed = parse_patch_name(patch_name)
    return json.dumps(
        {
            "product": "Cyra",
            "version": str(version),
            "requiresPatch": key,
            "requiresPatchVersion": ".".join(str(n) for n in parsed) if parsed else None,
            "requiresPatchName": str(patch_name),
            "source": "SVNManager (patch/release link)",
        },
        indent=2,
    ) + "\n"


# ---------------------------------------------------------------------------
# Working-copy / SVN helpers
# ---------------------------------------------------------------------------

def list_released_versions(wc_root):
    """Cyra versions present in the CyraReleases SVN (HEAD), local fallback."""
    releases_dir = os.path.join(wc_root, RELEASES_REL)
    versions = []
    try:
        info = run_svn(["svn", "info", "--show-item", "url", releases_dir])
        url = (info.stdout or "").strip()
        if info.returncode == 0 and url:
            result = run_svn(["svn", "list", "-r", "HEAD", url])
            if result.returncode == 0:
                versions = [ln.strip().rstrip("/") for ln in result.stdout.splitlines()]
    except Exception:
        versions = []
    if not versions and os.path.isdir(releases_dir):
        versions = [d for d in os.listdir(releases_dir) if parse_semver(d)]
    return [v for v in versions if parse_semver(v)]


def read_source_version(wc_root):
    path = os.path.join(wc_root, "cyra", "VERSION")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def gate_links_from_release_folders(wc_root, released_versions):
    """Fallback previous-link source: gate files already in release folders."""
    links = []
    for version in released_versions or []:
        path = os.path.join(wc_root, RELEASES_REL, version, "cyra-depends.json")
        try:
            with open(path, encoding="utf-8") as f:
                gate = json.load(f)
            links.append(
                {
                    "VERSION": gate.get("version") or version,
                    "REQUIRES_PATCH": gate.get("requiresPatch"),
                    "REQUIRES_PATCH_NAME": gate.get("requiresPatchName") or "",
                }
            )
        except (OSError, ValueError):
            continue
    return links


def apply_version_bump(wc_root, new_version, username):
    """Lock + update cyra/VERSION and core/__init__.py. Returns rel paths."""
    targets = [os.path.join(wc_root, p.replace("/", os.sep)) for p in VERSION_FILES]
    lock = run_svn(["svn", "lock", "--message", f"Locking by {username}"] + list(VERSION_FILES),
                   cwd=wc_root)
    if lock.returncode != 0:
        err = (lock.stderr or "").strip()
        # Already locked by the same user is fine (files selected in the UI).
        if "already locked" not in err or username not in err:
            raise RuntimeError(f"Could not lock Cyra version files: {err}")
    version_path, init_path = targets
    with open(version_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_version + "\n")
    with open(init_path, encoding="utf-8") as f:
        text = f.read()
    text, count = re.subn(
        r'^__version__\s*=\s*["\'][^"\']*["\']',
        f'__version__ = "{new_version}"',
        text,
        count=1,
        flags=re.M,
    )
    if count != 1:
        raise RuntimeError("Could not update __version__ in cyra/core/__init__.py")
    with open(init_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return list(VERSION_FILES)


# ---------------------------------------------------------------------------
# Plan / build / commit
# ---------------------------------------------------------------------------

def build_cyra_plan(db, wc_root, patch_name=None, patch_number=None):
    """Decide the release version and its dependency link.

    patch_name/patch_number: the patch being generated (cyra + web/db case).
    Without them (cyra only), the link is inherited from the previous release.
    """
    released = list_released_versions(wc_root)
    release_version = pick_release_version(released, read_source_version(wc_root))
    if release_version in released:
        raise RuntimeError(f"Cyra {release_version} already exists in {RELEASES_REL} SVN")

    if patch_name:
        link = {
            "REQUIRES_PATCH": resolve_patch_key(patch_number, patch_name),
            "REQUIRES_PATCH_NAME": patch_name,
            "SOURCE": f"new patch {patch_name}",
        }
    else:
        links = []
        try:
            links = db.get_cyra_release_links() or []
        except Exception:
            links = []
        prev = pick_previous_link(links, release_version)
        if prev is None:
            prev = pick_previous_link(gate_links_from_release_folders(wc_root, released), release_version)
        if prev is None:
            raise RuntimeError(
                "No previous Cyra release has a patch linked, so the new release "
                "cannot inherit a dependency. Link one on the Cyra Releases page first."
            )
        link = {
            "REQUIRES_PATCH": resolve_patch_key(prev["REQUIRES_PATCH"], prev["REQUIRES_PATCH_NAME"]),
            "REQUIRES_PATCH_NAME": prev["REQUIRES_PATCH_NAME"],
            "SOURCE": f"same patch as Cyra {prev['VERSION']} (no web/db change)",
        }
    return {
        "release_version": release_version,
        "link_patch": link["REQUIRES_PATCH"],
        "link_patch_name": link["REQUIRES_PATCH_NAME"],
        "link_source": link["SOURCE"],
    }


def find_release_for_patch(db, patch_name):
    """Highest Cyra release linked to a patch name, or None."""
    try:
        links = db.get_cyra_release_links() or []
    except Exception:
        return None
    matches = [l for l in links if (l.get("REQUIRES_PATCH_NAME") or "") == patch_name]
    if not matches:
        return None
    return max(matches, key=lambda l: parse_semver(l.get("VERSION")) or (0, 0, 0))


def build_update_plan(db, wc_root, patch_name):
    """Plan for PATCH MODIFICATION (update_patch) of a patch with Cyra files.

    Patch already linked to a Cyra release -> rebuild that same release
    from the current tree (no version bump, VERSION files untouched: the
    pack version comes from the build -Version override).
    Not linked yet -> create the next release, linked to this patch.
    """
    linked = find_release_for_patch(db, patch_name)
    if linked is not None:
        return {
            "release_version": linked["VERSION"],
            "link_patch": resolve_patch_key(linked.get("REQUIRES_PATCH"), patch_name),
            "link_patch_name": patch_name,
            "link_source": f"rebuild of Cyra {linked['VERSION']} already linked to {patch_name}",
            "rebuild": True,
        }
    plan = build_cyra_plan(db, wc_root, patch_name=patch_name)
    plan["rebuild"] = False
    return plan


# Everything a built dual pack must contain before SVNManager may commit
# it -- above all InstallCyra.cmd (top level + each side) and the GUI
# installer it launches. assemble_release.py already asserts this; the
# check is repeated here, on the tree AND inside the zip, because this
# is the last gate before the pack leaves the building.
REQUIRED_RELEASE_FILES = (
    "InstallCyra.cmd",
    "README_PLANT.txt",
    "release.json",
    "cyra-depends.json",
)
REQUIRED_SIDE_FILES = (
    "InstallCyra.cmd",
    "release.json",
    "plant_side.json",
    "README_RELEASE.txt",
    "requirements.txt",
    ".env.plant",
    "cyra-depends.json",
    "scripts/install_cyra_gui.ps1",
    "scripts/install_cyra_service.ps1",
    "scripts/install_python.ps1",
    "scripts/apply_cyra_release.ps1",
    "scripts/register_cyra_install.py",
)
RELEASE_SIDES = ("CyraTest", "CyraProd")


def required_release_paths():
    paths = list(REQUIRED_RELEASE_FILES)
    for side in RELEASE_SIDES:
        paths += [f"{side}/{rel}" for rel in REQUIRED_SIDE_FILES]
    return paths


def missing_release_files(out_dir):
    """Relative paths missing (or wrong) in the built release folder."""
    missing = []
    for rel in required_release_paths():
        if not os.path.isfile(os.path.join(out_dir, *rel.split("/"))):
            missing.append(rel)
    for rel in ["InstallCyra.cmd"] + [f"{s}/InstallCyra.cmd" for s in RELEASE_SIDES]:
        path = os.path.join(out_dir, *rel.split("/"))
        if os.path.isfile(path):
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                text = ""
            if "-WindowStyle Hidden" not in text or "install_cyra_gui.ps1" not in text:
                missing.append(f"{rel} (not the silent GUI-only launcher)")
    return missing


def verify_release_tree(out_dir, zip_path=None):
    """Raise RuntimeError unless folder (and zip, when given) is complete."""
    missing = missing_release_files(out_dir)
    if zip_path is not None:
        if not os.path.isfile(zip_path):
            missing.append(f"{os.path.basename(zip_path)} (release zip)")
        else:
            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
            for rel in required_release_paths():
                if rel not in names:
                    missing.append(f"in zip: {rel}")
    if missing:
        raise RuntimeError(
            "Cyra release pack is incomplete - refusing to commit it. "
            "Missing: " + ", ".join(missing)
        )
    return True


def build_and_commit_release(wc_root, plan, username, description="", status_callback=None):
    """Build the plant pack, embed the gate file, svn add + commit it."""
    def status(msg):
        if status_callback:
            status_callback(msg)

    version = plan["release_version"]
    cyra_root = os.path.join(wc_root, "cyra")
    out_dir = os.path.join(wc_root, RELEASES_REL, version)
    build_script = os.path.join(cyra_root, "scripts", "build_release.ps1")

    status(f"Building Cyra {version} release (this can take a few minutes)…")
    proc = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", build_script,
            "-PlantDual", "-Zip", "-Force",
            "-Version", version,
            "-Out", out_dir,
        ],
        cwd=cyra_root,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + "\n" + proc.stderr).splitlines()[-15:])
        raise RuntimeError(f"Cyra release build failed:\n{tail}")
    if not os.path.isfile(os.path.join(out_dir, "release.json")):
        raise RuntimeError(f"Build produced no release at {out_dir}")

    status("Writing cyra-depends.json gate file…")
    gate_text = gate_file_json(version, plan["link_patch"], plan["link_patch_name"])
    gate_paths = [os.path.join(out_dir, "cyra-depends.json")]
    for side in ("CyraTest", "CyraProd"):
        side_dir = os.path.join(out_dir, side)
        if os.path.isdir(side_dir):
            gate_paths.append(os.path.join(side_dir, "cyra-depends.json"))
    for gate_path in gate_paths:
        with open(gate_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(gate_text)

    zip_path = out_dir + ".zip"
    if os.path.isfile(zip_path):
        with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            for gate_path in gate_paths:
                arc = os.path.relpath(gate_path, out_dir).replace(os.sep, "/")
                if arc not in zf.namelist():
                    zf.write(gate_path, arc)

    # Last gate before commit: the folder AND the zip must contain the
    # whole installer (InstallCyra.cmd at the root and in each side, the
    # GUI script it launches, service/python/upgrade scripts, gate file).
    status("Verifying release pack is complete (InstallCyra.cmd, installer scripts, gate file, zip)…")
    verify_release_tree(out_dir, zip_path)

    status(f"Committing Cyra {version} release to SVN…")
    rel_dir = f"{RELEASES_REL}/{version}"
    rel_zip = f"{RELEASES_REL}/{version}.zip"
    add = run_svn(["svn", "add", "--force", rel_dir, rel_zip], cwd=wc_root)
    if add.returncode != 0:
        raise RuntimeError(f"svn add of Cyra release failed: {(add.stderr or '').strip()}")
    message = f"Cyra {version} release via SVNManager - requires patch {plan['link_patch_name']}"
    if description:
        message += f" - {description}"
    commit = run_svn(
        ["svn", "commit", "--username", username, "--message", message, rel_dir, rel_zip],
        cwd=wc_root,
    )
    if commit.returncode != 0:
        raise RuntimeError(f"svn commit of Cyra release failed: {(commit.stderr or '').strip()}")
    m = re.search(r"Committed revision (\d+)", commit.stdout or "")
    return {"version": version, "revision": m.group(1) if m else ""}


def record_cyra_link(db, plan):
    """Write the link into DEV_TOOL.CYRA_RELEASE and commit."""
    svn_path = f"svn://10.31.10.249/{RELEASES_REL}/{plan['release_version']}"
    db.set_cyra_release_link(
        plan["release_version"], plan["link_patch"], plan["link_patch_name"], svn_path
    )
    db.conn.commit()
