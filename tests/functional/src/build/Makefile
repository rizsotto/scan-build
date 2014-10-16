PROGRAM = prg

GOODS = ../main.o ../clean-one.o ../clean-two.o ../emit-one.o ../emit-two.o
CLEANS = ../main.o ../clean-one.o ../clean-two.o
BADS = ../main.o ../broken-one.o ../broken-two.o


CXXFLAGS = -Wall -DDEBUG -Dvariable=value -I../include
CFLAGS = -Wall -DDEBUG -Dvariable="value with space" -I ../include
LDFLAGS =

%.o: %.c
	$(CC) -c -o $@ $< $(CFLAGS)

%.o: %.cpp
	$(CXX) -c -o $@ $< $(CXXFLAGS)

$(PROGRAM): $(GOODS)
	$(CXX) -o $@ $^ $(LDFLAGS)

reset:
	rm -rf $(PROGRAM) $(GOODS) $(BADS) $(CLEANS)

regular: reset $(GOODS) $(PROGRAM)

clean: reset $(CLEANS)

broken: reset $(BADS)
