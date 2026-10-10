"""Merge checks; all repository deletion happens in temporary directories."""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location(
    "merge_tool", Path(__file__).resolve().parents[1] / "main.py"
)
merge_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge_tool)

HUNK = b"<<<<<<< HEAD\r\nhead\r\n=======\r\nfeature\r\n>>>>>>> feature\r\n"


class LossStreakTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repository = Path(temporary.name)
        self.git_dir = self.repository / ".git"
        self.git_dir.mkdir()
        (self.git_dir / "objects").mkdir()
        (self.git_dir / "objects" / "sample").write_bytes(b"history")
        self.streak_file = self.repository / merge_tool.LOSS_STREAK_FILE
        nested = self.repository / "src"
        nested.mkdir()
        self.merged = nested / "merged.txt"
        self.inputs = [self.repository / name for name in ("base", "local", "remote")]
        for path in self.inputs:
            path.write_bytes(b"input\r\n")
        self.output = io.StringIO()
        self.capture = contextlib.redirect_stdout(self.output)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)

    def run_merge(self, results, content=HUNK):
        self.merged.write_bytes(content)
        game = Mock()
        game.main.side_effect = results
        argv = ["main.py", *map(str, self.inputs), str(self.merged)]
        with patch.object(merge_tool, "load_game", return_value=game), \
                patch("sys.argv", argv), contextlib.redirect_stderr(self.output):
            status = merge_tool.main()
        return status, game

    def test_losses_persist_across_runs_and_delete_only_on_third(self):
        for expected in (1, 2):
            status, _ = self.run_merge([False])
            self.assertEqual(status, 0)
            self.assertEqual(self.streak_file.read_text(), f"{expected}\n")
            self.assertTrue(self.git_dir.is_dir())
            self.assertEqual(self.merged.read_bytes(), b"head\r\n")
        status, _ = self.run_merge([False])
        self.assertEqual(status, 1)
        self.assertEqual(self.streak_file.read_text(), "3\n")
        self.assertFalse(self.git_dir.exists())
        self.assertEqual(self.merged.read_bytes(), HUNK)
        for path in self.inputs:
            self.assertEqual(path.read_bytes(), b"input\r\n")

    def test_win_resets_streak_and_preserves_winning_bytes(self):
        self.streak_file.write_text("2\n")
        content = b"before\r\n" + HUNK + b"between\n" + HUNK + b"after"
        status, game = self.run_merge([True, False], content)
        self.assertEqual(status, 0)
        self.assertEqual(game.main.call_count, 2)
        self.assertEqual(self.streak_file.read_text(), "1\n")
        self.assertTrue(self.git_dir.is_dir())
        self.assertEqual(
            self.merged.read_bytes(), b"before\r\nfeature\r\nbetween\nhead\r\nafter"
        )

    def test_third_loss_stops_remaining_hunks(self):
        content = HUNK * 4
        status, game = self.run_merge([False, False, False, True], content)
        self.assertEqual(status, 1)
        self.assertEqual(game.main.call_count, 3)
        self.assertFalse(self.git_dir.exists())
        self.assertEqual(self.merged.read_bytes(), content)

    def test_quit_does_not_change_streak_or_merged_file(self):
        self.streak_file.write_text("2\n")
        status, _ = self.run_merge([None])
        self.assertEqual(status, 1)
        self.assertEqual(self.streak_file.read_text(), "2\n")
        self.assertTrue(self.git_dir.is_dir())
        self.assertEqual(self.merged.read_bytes(), HUNK)

    def test_completed_results_count_before_later_quit(self):
        status, _ = self.run_merge([False, None], HUNK * 2)
        self.assertEqual(status, 1)
        self.assertEqual(self.streak_file.read_text(), "1\n")
        self.assertEqual(self.merged.read_bytes(), HUNK * 2)

    def test_malformed_counter_stops_before_battle(self):
        for value in ("-1", "garbage", "", "2.5"):
            with self.subTest(value=value):
                self.streak_file.write_text(value)
                status, game = self.run_merge([False])
                self.assertEqual(status, 1)
                game.main.assert_not_called()
                self.assertTrue(self.git_dir.is_dir())
                self.assertEqual(self.merged.read_bytes(), HUNK)

    def test_deletion_failure_leaves_merged_untouched(self):
        self.streak_file.write_text("2\n")
        with patch.object(merge_tool.shutil, "rmtree", side_effect=OSError("denied")):
            status, _ = self.run_merge([False])
        self.assertEqual(status, 1)
        self.assertEqual(self.streak_file.read_text(), "3\n")
        self.assertTrue(self.git_dir.is_dir())
        self.assertEqual(self.merged.read_bytes(), HUNK)

    def test_failed_counter_save_does_not_delete_repository(self):
        self.streak_file.write_text("2\n")
        with patch.object(merge_tool.os, "replace", side_effect=OSError("denied")):
            status, _ = self.run_merge([False])
        self.assertEqual(status, 1)
        self.assertEqual(self.streak_file.read_text(), "2\n")
        self.assertTrue((self.git_dir / "objects" / "sample").is_file())
        self.assertEqual(self.merged.read_bytes(), HUNK)
        self.assertEqual(list(self.repository.glob(merge_tool.LOSS_STREAK_FILE + ".*")), [])

    def test_worktree_git_file_is_rejected_without_following_pointer(self):
        worktree = self.repository / "worktree"
        worktree.mkdir()
        (worktree / ".git").write_text(f"gitdir: {self.git_dir}\n")
        with self.assertRaises(ValueError):
            merge_tool.find_repository_root(worktree / "merged.txt")
        self.assertTrue(self.git_dir.is_dir())

    def test_symlinked_git_directory_is_rejected(self):
        worktree = self.repository / "symlinked"
        worktree.mkdir()
        (worktree / ".git").symlink_to(self.git_dir, target_is_directory=True)
        with self.assertRaises(ValueError):
            merge_tool.find_repository_root(worktree / "merged.txt")
        self.assertTrue((self.git_dir / "objects" / "sample").is_file())

    def test_no_conflicts_or_malformed_markers_do_not_record_results(self):
        for content, expected in ((b"clean\r\n", 0), (b"<<<<<<< HEAD\nhead", 1)):
            with self.subTest(content=content):
                status, game = self.run_merge([], content)
                self.assertEqual(status, expected)
                game.main.assert_not_called()
                self.assertFalse(self.streak_file.exists())
                self.assertEqual(self.merged.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
