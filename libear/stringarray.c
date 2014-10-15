/* -*- coding: utf-8 -*-
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
*/

#include "stringarray.h"

#include <ctype.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

char const ** bear_strings_build(char const * const arg, va_list *args)
{
    char const ** result = 0;
    size_t size = 0;
    for (char const * it = arg; it; it = va_arg(*args, char const *))
    {
        result = realloc(result, (size + 1) * sizeof(char const *));
        if (0 == result)
        {
            perror("bear: realloc");
            exit(EXIT_FAILURE);
        }
        char const * copy = strdup(it);
        if (0 == copy)
        {
            perror("bear: strdup");
            exit(EXIT_FAILURE);
        }
        result[size++] = copy;
    }
    result = realloc(result, (size + 1) * sizeof(char const *));
    if (0 == result)
    {
        perror("bear: realloc");
        exit(EXIT_FAILURE);
    }
    result[size++] = 0;

    return result;
}

char const ** bear_strings_copy(char const ** const in)
{
    size_t const size = bear_strings_length(in);

    char const ** const result = malloc((size + 1) * sizeof(char const *));
    if (0 == result)
    {
        perror("bear: malloc");
        exit(EXIT_FAILURE);
    }

    char const ** out_it = result;
    for (char const * const * in_it = in; (in_it) && (*in_it); ++in_it, ++out_it)
    {
        *out_it = strdup(*in_it);
        if (0 == *out_it)
        {
            perror("bear: strdup");
            exit(EXIT_FAILURE);
        }
    }
    *out_it = 0;
    return result;
}

char const ** bear_strings_append(char const ** const in, char const * const e)
{
    if (0 == e)
        return in;

    size_t size = bear_strings_length(in);
    char const ** result = realloc(in, (size + 2) * sizeof(char const *));
    if (0 == result)
    {
        perror("bear: realloc");
        exit(EXIT_FAILURE);
    }
    result[size++] = e;
    result[size++] = 0;
    return result;
}

size_t bear_strings_length(char const * const * const in)
{
    size_t result = 0;
    for (char const * const * it = in; (it) && (*it); ++it)
        ++result;
    return result;
}

void bear_strings_release(char const ** in)
{
    for (char const * const * it = in; (it) && (*it); ++it)
    {
        free((void *)*it);
    }
    free((void *)in);
}
