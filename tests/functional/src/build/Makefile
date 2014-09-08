PROGRAM = prg

OBJS = ../main.o ../clean-one.o ../clean-two.o ../emit-one.o ../emit-two.o


CXXFLAGS = -Wall -DDEBUG -Dvariable=value -I../include
CFLAGS = -Wall -DDEBUG -Dvariable="value with space" -I ../include
LDFLAGS =

all: $(PROGRAM)

test: all

%.o: %.c
	$(CC) -c -o $@ $< $(CFLAGS)

%.o: %.cpp
	$(CXX) -c -o $@ $< $(CXXFLAGS)

$(PROGRAM): $(OBJS)
	$(CXX) -o $@ $^ $(LDFLAGS)

clean:
	rm -rf $(OBJS) $(PROGRAM)
