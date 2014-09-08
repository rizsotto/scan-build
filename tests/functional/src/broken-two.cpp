class A
{
    public:
        A() {}
       ~A() {}

    private:
        A(const A&);
        A & operator=(const A&);

};

void test_A_copy()
{
    A a;
    A b = a;
}
