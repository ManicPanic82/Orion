"""Tests for ProjectManager root validation."""

from __future__ import annotations

import pytest

from orion.projects import ProjectManager


def test_project_inside_allowed_root_accepted(tmp_path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    mgr = ProjectManager(allowed_roots=[str(tmp_path)])
    project = mgr.register_project("p", str(root))
    assert project.root == str(root.resolve())


def test_sibling_prefix_directory_rejected(tmp_path) -> None:
    # Regression: the old startswith check accepted any root whose path text
    # begins with the allowed root's text (e.g. "proj2" for allowed root
    # "proj"), even though it is a sibling, not a child.
    allowed = tmp_path / "proj"
    allowed.mkdir()
    sibling = tmp_path / "proj2"
    sibling.mkdir()
    mgr = ProjectManager(allowed_roots=[str(allowed)])
    with pytest.raises(ValueError, match="outside allowed roots"):
        mgr.register_project("evil", str(sibling))


def test_nested_project_inside_allowed_root_accepted(tmp_path) -> None:
    root = tmp_path / "a" / "b"
    root.mkdir(parents=True)
    mgr = ProjectManager(allowed_roots=[str(tmp_path)])
    project = mgr.register_project("nested", str(root))
    assert project.root == str(root.resolve())
