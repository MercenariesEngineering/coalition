#!/bin/sh
cd ../..
tar -cvzf install/linux/coalition.tar.gz coalition.ini control.py job.py LICENCE public_html/* server.py worker.py host_mem.py host_cpu.py --exclude=".svn"
