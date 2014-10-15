/* -*- coding: utf-8 -*-
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
*/

#include "config.h"
#include "environ.h"
#include "stringarray.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef HAVE_NSGETENVIRON
#include <crt_externs.h>
#else
// Some platforms don't provide environ in any header.
extern char **environ;
#endif


char const * * bear_update_environ(char const * envs[], char const * key)
{
    char const * const value = getenv(key);
    if (0 == value)
    {
        perror("bear: getenv");
        exit(EXIT_FAILURE);
    }
    // find the key if it's there
    size_t const key_length = strlen(key);
    char const * * it = envs;
    for (; (it) && (*it); ++it)
    {
        if ((0 == strncmp(*it, key, key_length)) &&
            (strlen(*it) > key_length) &&
            ('=' == (*it)[key_length]))
            break;
    }
    // check the value might already correct
    char const * * result = envs;
    if ((0 != it) && ((0 == *it) || (strcmp(*it + key_length + 1, value))))
    {
        char * env = 0;
        if (-1 == asprintf(&env, "%s=%s", key, value))
        {
            perror("bear: asprintf");
            exit(EXIT_FAILURE);
        }
        if (*it)
        {
            free((void *)*it);
            *it = env;
        }
        else
            result = bear_strings_append(envs, env);
    }
    return result;
}

char * * bear_get_environ(void)
{
#ifdef HAVE_NSGETENVIRON
    // environ is not available for shared libraries have to use _NSGetEnviron()
    return *_NSGetEnviron();
#else
    return environ;
#endif
}
