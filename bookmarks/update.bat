@ECHO OFF
PUSHD .

set DIR1=bookmarks
set DIR2=eric-bixby.github.io

set FILE1=index.html
set FILE2=bookmarks.html

set NOTE="Update bookmarks"

call cd_git %DIR1% && git pull && call cd_git %DIR2% && git pull

call cd_git %DIR1% && parse.py && git add -A && git commit -m %NOTE% && git push && copy %FILE1% ..\%DIR2%\%FILE2%
call cd_git %DIR2% && git add -A && git commit -m %NOTE% && git push

POPD
