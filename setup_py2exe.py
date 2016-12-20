#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4

from distutils.core import setup
import py2exe
setup(service=['server', 'worker_service'], console=['worker.py','control.py'], options = {"py2exe": { "dll_excludes": ["MSWSOCK.dll","POWRPROF.dll"]}})
