: RUN: %s %T\successful_build
: RUN: cd %T\successful_build; intercept-build -vvv --override-compiler --cdb wrapper.json run.bat
: RUN: cd %T\successful_build; cdb_diff wrapper.json expected.json

set root_dir=%1

mkdir "%root_dir%"
mkdir "%root_dir%\src"

copy /y nul "%root_dir%\src\empty.c"

echo ^
%%CC%% -c -o src\empty.o -Dver=1 src\empty.c ^

^

%%CXX%% -c -o src\empty.o -Dver=2 src\empty.c ^

^

cd src ^

^

%%CC%% -c -o empty.o -Dver=3 empty.c ^

^

%%CXX%% -c -o empty.o -Dver=4 empty.c ^

> "%root_dir%\run.bat"

set output="%root_dir%\expected.json"
del /f %output%

cd "%root_dir%"
cdb_expect ^
    --cdb %output% ^
    --command "cc -c -o src\empty.o -Dver=1 src\empty.c" ^
    --file "%root_dir%\src\empty.c"
cdb_expect ^
    --cdb %output% ^
    --command "c++ -c -o src\empty.o -Dver=2 src\empty.c" ^
    --file "%root_dir%\src\empty.c"
cd src
cdb_expect ^
    --cdb %output% ^
    --command "cc -c -o empty.o -Dver=3 empty.c" ^
    --file "%root_dir%\src\empty.c"
cdb_expect ^
    --cdb %output% ^
    --command "c++ -c -o empty.o -Dver=4 empty.c" ^
    --file "%root_dir%\src\empty.c"
