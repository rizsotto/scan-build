#include <cassert>

int div(int numerator, int denominator)
{
    return numerator / denominator;
}

void div_test()
{
    for (int i = 0; i < 2; ++i)
        assert(div(2 * i, i) == 2);
}
