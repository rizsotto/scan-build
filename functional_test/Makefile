CXXFLAGS = -Wall
LDFLAGS =
OBJS = dead_code.o divide_zero.o leak.o main.o null_dereference.o

%.o: %.cpp
	$(CXX) -c -o $@ $< $(CXXFLAGS)

test: $(OBJS)
	$(CXX) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(OBJS) ./test
