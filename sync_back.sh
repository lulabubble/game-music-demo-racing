#!/bin/sh -ex

home_regex=/data/data/com\\.termux/files/home
dir=`pwd | sed "s,^$home_regex/,,"`

rsync -rltv \
      --include='*/' \
      --include='*.py' \
      --include='*.html' \
      --include='*.json' \
      --include='*.md' \
      --exclude='*' \
      /sdcard/mycode/$dir/ ~/$dir/
