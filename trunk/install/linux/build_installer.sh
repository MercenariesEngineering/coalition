#!/bin/sh
cd ../..
tar -cvzf install/linux/coalition.tar.gz coalition.ini control.py job.py LICENCE public_html/*   server.py worker.py --exclude=".svn"