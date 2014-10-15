/* -*- coding: utf-8 -*-
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
*/

#include "protocol.h"
#include "stringarray.h"

#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>


void bear_write_message(int fd, bear_message_t const * e)
{
    static int const RS = 0x1e;
    static int const US = 0x1f;
    dprintf(fd, "%d%c", e->pid, RS);
    dprintf(fd, "%d%c", e->ppid, RS);
    dprintf(fd, "%s%c", e->fun, RS);
    dprintf(fd, "%s%c", e->cwd, RS);
    size_t const length = bear_strings_length(e->cmd);
    for (size_t it = 0; it < length; ++it)
    {
        dprintf(fd, "%s%c", e->cmd[it], US);
    }
}

void bear_send_message(char const * destination, bear_message_t const * msg)
{
    char * filename = 0;
    if (-1 == asprintf(&filename, "%s/cmd.XXXXXX", destination))
    {
        perror("bear: asprintf");
        exit(EXIT_FAILURE);
    }
    int fd = mkstemp(filename);
    free((void *)filename);
    if (-1 == fd)
    {
        perror("bear: open");
        exit(EXIT_FAILURE);
    }
    bear_write_message(fd, msg);
    close(fd);
}
