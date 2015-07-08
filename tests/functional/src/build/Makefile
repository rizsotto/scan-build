SRCDIR := ..
OBJDIR := .

GOOD_SRCS := main.c clean-one.c clean-two.c emit-one.c emit-two.c
CLEAN_SRCS := main.c clean-one.c clean-two.c
BAD_SRCS := main.c broken-one.c broken-two.c


GOOD_OBJS = $(GOOD_SRCS:%.c=$(OBJDIR)/%.o)
CLEAN_OBJS = $(CLEAN_SRCS:%.c=$(OBJDIR)/%.o)
BAD_OBJS = $(BAD_SRCS:%.c=$(OBJDIR)/%.o)

PROGRAM = $(OBJDIR)/prg

CC := clang
CFLAGS = -Wall -DDEBUG -Dvariable="value with space" -I $(SRCDIR)/include
LDFLAGS =


$(OBJDIR)/%.o: $(SRCDIR)/%.c
	$(CC) -c -o $@ $< $(CFLAGS)

$(PROGRAM): $(GOOD_OBJS)
	$(CC) -o $@ $^ $(LDFLAGS)

build_regular: $(GOOD_OBJS) $(PROGRAM)

build_clean: $(CLEAN_OBJS)

build_broken: $(BAD_OBJS)

build_all_in_one:
	$(CC) -o $(PROGRAM) $(CFLAGS) $(LDFLAGS) $(CLEAN_SRCS:%.c=$(SRCDIR)/%.c)

clean:
	rm -f $(PROGRAM) $(OBJDIR)/*.o
