#!/bin/sh

DIR1=~/git/bookmarks
FILE1=index.html
DIR2=~/git/eric-bixby.github.io
FILE2=bookmarks.html
NOTE="Update bookmarks"

cd $DIR1 && git pull && cd $DIR2 && git pull

cd $DIR1 && ./parse.py && git add -A && git commit -m "$NOTE" && git push && cp $DIR1/$FILE1 $DIR2/$FILE2
cd $DIR2 && git add -A && git commit -m "$NOTE" && git push
