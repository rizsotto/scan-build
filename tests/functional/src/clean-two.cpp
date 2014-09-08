extern "C"
{
#include <clean-one.h>
}

void set_dots_method()
{
    unsigned int const size = do_nothing_loop();
    char * leak = new char[size];

    for (unsigned int idx = 0; idx < size; ++idx)
    {
        leak[idx] = '.';
    }
    delete [] leak;
}
