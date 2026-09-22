"""对 python_utils.fs 的测试。"""

from python_utils import fs


def test_tree_limits_depth(tmp_path):
    (tmp_path / "a" / "b" / "c").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c" / "f.txt").write_text("x")
    paths = fs.tree(str(tmp_path), max_depth=1)
    assert any("a" in p for p in paths)


def test_iter_files_ext(tmp_path):
    (tmp_path / "x.py").write_text("")
    (tmp_path / "y.md").write_text("")
    py = list(fs.iter_files(str(tmp_path), ext=".py"))
    assert len(py) == 1
