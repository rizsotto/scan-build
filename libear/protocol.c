/*  Copyright (C) 2012-2014 by László Nagy
    This file is part of Bear.

    Bear is a tool to generate compilation database for clang tooling.

    Bear is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Bear is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
