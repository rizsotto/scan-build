
int dead_code_test()
{
    int i = 128;
    int j = i;

    for (int idx = i; idx > 0; --idx)
        i -= idx;

    return i;
}
