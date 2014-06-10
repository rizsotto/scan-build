
int dead_code_test()
{
    int i = 128;
    int idx = 0;

    for (idx = i; idx > 0; --idx)
        i -= idx;

    return i;

    if (idx > i) return 0;
}
