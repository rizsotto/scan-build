/* -*- coding: utf-8 -*-
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
*/

#pragma once

#include <stddef.h>
#include <stdarg.h>

char const ** bear_strings_build(char const * arg, va_list *ap);

char const ** bear_strings_copy(char const ** const in);
char const ** bear_strings_append(char const ** in, char const * e);

size_t        bear_strings_length(char const * const * in);

void          bear_strings_release(char const **);
