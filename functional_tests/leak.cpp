
void leak_test_method()
{
    unsigned int const size = 128;

    char * leak = new char[size];

    for (unsigned int idx = 0; idx < size + 9; ++idx)
    {
        leak[idx] = '.';
    }

    delete leak;
}
