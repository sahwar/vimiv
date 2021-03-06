# vim: ft=python fileencoding=utf-8 sw=4 et sts=4
"""Mark tests for vimiv's test suite."""

import os
from unittest import main

from vimiv_testcase import VimivTestCase


class MarkTest(VimivTestCase):
    """Mark Tests."""

    @classmethod
    def setUpClass(cls):
        cls.init_test(cls, ["vimiv/testimages"])
        # Move away from directory
        cls.vimiv["library"].scroll("j")

    def test_mark(self):
        """Mark images."""
        # Mark
        self.vimiv["mark"].mark()
        expected_marked = [os.path.abspath("arch-logo.png")]
        self.assertEqual(expected_marked, self.vimiv["mark"].marked)
        # Remove mark
        self.vimiv["mark"].mark()
        self.assertEqual([], self.vimiv["mark"].marked)

    def test_toggle_mark(self):
        """Toggle marks."""
        self.vimiv["mark"].mark()
        self.vimiv["mark"].toggle_mark()
        self.assertEqual([], self.vimiv["mark"].marked)
        self.vimiv["mark"].toggle_mark()
        expected_marked = [os.path.abspath("arch-logo.png")]
        self.assertEqual(expected_marked, self.vimiv["mark"].marked)

    def test_mark_all(self):
        """Mark all."""
        self.vimiv["mark"].mark_all()
        expected_marked = ["arch-logo.png", "arch_001.jpg", "symlink_to_image",
                           "vimiv.bmp", "vimiv.svg", "vimiv.tiff"]
        expected_marked = [os.path.abspath(image) for image in expected_marked]
        self.assertEqual(expected_marked, self.vimiv["mark"].marked)

    def test_mark_between(self):
        """Mark between."""
        self.vimiv["mark"].mark()
        self.vimiv["eventhandler"].set_num_str(3)
        self.vimiv["library"].scroll("j")
        self.vimiv["mark"].mark()
        self.vimiv["mark"].mark_between()
        expected_marked = ["arch-logo.png", "arch_001.jpg", "symlink_to_image"]
        expected_marked = [os.path.abspath(image) for image in expected_marked]
        self.assertEqual(expected_marked, self.vimiv["mark"].marked)

    def test_fail_mark(self):
        """Fail marking."""
        # Directory
        while not os.path.isdir(self.vimiv.get_pos(True)):
            self.vimiv["library"].scroll("j")
        self.vimiv["mark"].mark()
        self.check_statusbar("WARNING: Marking directories is not supported")
        # Too less images for mark between
        self.vimiv["mark"].mark_between()
        self.check_statusbar("ERROR: Not enough marks")

    def tearDown(self):
        self.vimiv["mark"].marked = []
        self.vimiv["library"].move_pos(False)
        self.vimiv["library"].scroll("j")


if __name__ == "__main__":
    main()
