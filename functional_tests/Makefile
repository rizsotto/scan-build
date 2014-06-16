PROGRAM = prg
CXXFLAGS = -Wall
CFLAGS = -Wall
LDFLAGS =
OBJS = dead_code.o divide_zero.o leak.o main.o null_dereference.o not_used_attributes.o

all: $(PROGRAM)

test: all

%.o: %.c
	$(CC) -c -o $@ $< $(CFLAGS)

%.o: %.cpp
	$(CXX) -c -o $@ $< $(CXXFLAGS)

$(PROGRAM): $(OBJS)
	$(CXX) -o $@ $^ $(LDFLAGS)

clean:
	rm -rf $(OBJS) $(PROGRAM) *.plist
