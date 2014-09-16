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

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>


static int init_socket(char const * file, struct sockaddr_un * addr);

static ssize_t socket_write(int fd, uint8_t const * buf, ssize_t nbyte)
{
    ssize_t sum = 0;
    while (sum != nbyte)
    {
        ssize_t const cur = write(fd, buf + sum, nbyte - sum);
        if (-1 == cur)
        {
            return cur;
        }
        sum += cur;
    }
    return sum;
}

static void write_pid(int fd, pid_t pid)
{
    socket_write(fd, (uint8_t const *)&pid, sizeof(pid_t));
}

static void write_string(int fd, char const * message)
{
    size_t const length = (message) ? strlen(message) : 0;
    socket_write(fd, (uint8_t const *)&length, sizeof(size_t));
    if (length > 0)
    {
        socket_write(fd, (uint8_t const *)message, length);
    }
}

static void write_string_array(int fd, char const * const * message)
{
    size_t const length = bear_strings_length(message);
    socket_write(fd, (uint8_t const *)&length, sizeof(size_t));
    for (size_t it = 0; it < length; ++it)
    {
        write_string(fd, message[it]);
    }
}

void bear_write_message(int fd, bear_message_t const * e)
{
    write_pid(fd, e->pid);
    write_pid(fd, e->ppid);
    write_string(fd, e->fun);
    write_string(fd, e->cwd);
    write_string_array(fd, e->cmd);
}

void bear_send_message(char const * file, bear_message_t const * msg)
{
    struct sockaddr_un addr;
    int s = init_socket(file, &addr);
    if (-1 == connect(s, (struct sockaddr *)&addr, sizeof(struct sockaddr_un)))
    {
        perror("bear: connect");
        exit(EXIT_FAILURE);
    }
    bear_write_message(s, msg);
    close(s);
}

static int init_socket(char const * file, struct sockaddr_un * addr)
{
    int const s = socket(AF_UNIX, SOCK_STREAM, 0);
    if (-1 == s)
    {
        perror("bear: socket");
        exit(EXIT_FAILURE);
    }
    memset((void *)addr, 0, sizeof(struct sockaddr_un));
    addr->sun_family = AF_UNIX;
    strncpy(addr->sun_path, file, sizeof(addr->sun_path) - 1);
    return s;
}
