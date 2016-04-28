# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
# RUN: %{python} %s

import libear as sut
import unittest
import os.path


class TemporaryDirectoryTest(unittest.TestCase):
    def test_creates_directory(self):
        dir_name = None
        with sut.temporary_directory() as tmpdir:
            self.assertTrue(os.path.isdir(tmpdir))
            dir_name = tmpdir
        self.assertIsNotNone(dir_name)
        self.assertFalse(os.path.exists(dir_name))

    def test_removes_directory_when_exception(self):
        dir_name = None
        try:
            with sut.temporary_directory() as tmpdir:
                self.assertTrue(os.path.isdir(tmpdir))
                dir_name = tmpdir
                raise RuntimeError('message')
        except:
            self.assertIsNotNone(dir_name)
            self.assertFalse(os.path.exists(dir_name))


if __name__ == '__main__':
    unittest.main()
