# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import beye.analyze as sut

def test_split_arguments():
    input = ['clang', '-Wall', '-std=C99', '-v', 'file.c']
    expected = ['clang', '-Wall', '-std', 'C99', '-v', 'file.c']
    assert expected == sut.split_arguments(input)
