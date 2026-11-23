"""BUILD STEP - packages the application into one versioned zip (the CI/CD "artifact").

    python scripts/package.py

Python has no compile step, so "building" means: collect exactly the files the server needs
(the app, requirements.txt, VERSION), stamp a BUILD_ID into the package, and zip them as

    build-<VERSION>-<BUILD_ID>.zip      e.g. build-1.1.0-run42-1a2b3c4.zip

The BUILD_ID is made from the GitHub Actions run number and commit, and the running app
reports it on /health, which is how the pipeline proves that exact build is live.
Tests, the workflow and other repo files are NOT shipped to production.
"""
import argparse
import os
import zipfile
from pathlib import Path

INCLUDE_DIRS = ["app"]
INCLUDE_FILES = ["requirements.txt", "VERSION"]
SKIP_DIR_NAMES = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def make_build_id(env=None) -> str:
    env = os.environ if env is None else env
    run_number = env.get("GITHUB_RUN_NUMBER", "local")
    short_sha = env.get("GITHUB_SHA", "")[:7] or "nogit"
    return f"run{run_number}-{short_sha}"


def build_package(root: Path, out_dir: Path, build_id: str) -> Path:
    root, out_dir = Path(root), Path(out_dir)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"build-{version}-{build_id}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE_FILES:
            zf.write(root / name, name)
        for folder in INCLUDE_DIRS:
            for path in sorted((root / folder).rglob("*")):
                relative = path.relative_to(root)
                if path.is_dir() or SKIP_DIR_NAMES & set(relative.parts) or path.suffix in SKIP_SUFFIXES:
                    continue
                zf.write(path, relative.as_posix())
        zf.writestr("BUILD_ID", build_id + "\n")
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the application for deployment.")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], help="project folder")
    parser.add_argument("--out", default=None, help="output folder (default: <root>/dist)")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out) if args.out else root / "dist"
    build_id = make_build_id()
    zip_path = build_package(root, out_dir, build_id)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()

    print(f"Built {zip_path.name} ({zip_path.stat().st_size} bytes)")
    print(f"  version  : {version}")
    print(f"  build id : {build_id}")

    # Hand the values to the next pipeline jobs (only set when running inside GitHub Actions)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"artifact={zip_path.name}\n")
            fh.write(f"build_id={build_id}\n")
            fh.write(f"version={version}\n")


if __name__ == "__main__":
    main()
