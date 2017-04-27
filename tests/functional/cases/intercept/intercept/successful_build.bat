: RUN: %s %T\successful_build
: RUN: cd %T\successful_build; %{expect} --cdb expected.json --command "cc -c -Dver=1 src\empty.c" --file "src\empty.c"
: RUN: cd %T\successful_build; %{expect} --cdb expected.json --command "c++ -c -Dver=2 src\empty.c" --file "src\empty.c"
: RUN: cd %T\successful_build; %{expect} --cdb expected.json --command "cc -c -Dver=3 src\empty.c" --file "src\empty.c"
: RUN: cd %T\successful_build; %{expect} --cdb expected.json --command "c++ -c -Dver=4 src\empty.c" --file "src\empty.c"
: RUN: cd %T\successful_build; %{intercept-build} --override-compiler --cdb wrapper.json run.bat
: RUN: cd %T\successful_build; %{cdb_diff} wrapper.json expected.json

set root_dir=%1

mkdir "%root_dir%"
mkdir "%root_dir%\src"

copy /y nul "%root_dir%\src\empty.c"

echo ^
%%CC%% -c -Dver=1 src\empty.c ^

^

%%CXX%% -c -Dver=2 src\empty.c ^

^

%%CC%% -c -Dver=3 src\empty.c ^

^

%%CXX%% -c -Dver=4 src\empty.c ^

> "%root_dir%\run.bat"

set output="%root_dir%\expected.json"
del /f %output%