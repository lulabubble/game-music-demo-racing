#!/bin/sh -ex

home_regex=/data/data/com\\.termux/files/home
dir=`pwd | sed "s,^$home_regex/,,"`

rsync -rltv --delete --delete-excluded \
      --exclude='.git/' \
      --exclude='*.opus' \
      ~/$dir/ /sdcard/mycode/$dir
