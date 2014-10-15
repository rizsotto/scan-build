/* -*- coding: utf-8 -*-
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
*/

#pragma once

#include <unistd.h>

typedef struct bear_message_t
{
    pid_t pid;
    pid_t ppid;
    char const * fun;
    char const * cwd;
    char const * * cmd;
} bear_message_t;

void bear_write_message(int fd, bear_message_t const * e);

void bear_send_message(char const * destination, bear_message_t const * e);
