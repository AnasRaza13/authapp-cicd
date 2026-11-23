"""Tests for the build step (scripts/package.py)."""
import zipfile

from scripts.package import build_package, make_build_id


def make_project(root):
    (root / "app" / "sub").mkdir(parents=True)
    (root / "app" / "main.py").write_text("print('hi')")
    (root / "app" / "sub" / "mod.py").write_text("x = 1")
    (root / "app" / "__pycache__").mkdir()
    (root / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"junk")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text("")
    (root / ".github").mkdir()
    (root / "requirements.txt").write_text("fastapi\n")
    (root / "VERSION").write_text("2.3.4\n")
    return root


def test_zip_name_contains_version_and_build_id(tmp_path):
    root = make_project(tmp_path / "project")
    zip_path = build_package(root, tmp_path / "dist", "run7-abc1234")
    assert zip_path.name == "build-2.3.4-run7-abc1234.zip"


def test_zip_contains_the_app_requirements_version_and_build_id(tmp_path):
    root = make_project(tmp_path / "project")
    zip_path = build_package(root, tmp_path / "dist", "run7-abc1234")
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert {"app/main.py", "app/sub/mod.py", "requirements.txt", "VERSION", "BUILD_ID"} <= names
        assert zf.read("BUILD_ID").decode().strip() == "run7-abc1234"
        assert zf.read("VERSION").decode().strip() == "2.3.4"


def test_zip_leaves_out_tests_bytecode_and_workflow_files(tmp_path):
    root = make_project(tmp_path / "project")
    zip_path = build_package(root, tmp_path / "dist", "run7-abc1234")
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            assert not name.startswith(("tests/", ".github/"))
            assert "__pycache__" not in name and not name.endswith(".pyc")


def test_build_id_comes_from_github_variables():
    env = {"GITHUB_RUN_NUMBER": "42", "GITHUB_SHA": "abcdef1234567890"}
    assert make_build_id(env) == "run42-abcdef1"
    assert make_build_id({}) == "runlocal-nogit"
