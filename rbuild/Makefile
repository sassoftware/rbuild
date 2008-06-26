#
# Copyright (c) 2006-2008 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

python_files =  __init__.py	\
                errors.py \
                handle.py \
                rbuildcfg.py \
                ui.py

dist_files = Makefile constants.py.in $(python_files)

SUBDIRS = internal pluginapi facade

all: default-subdirs default-all constants.py

constants.py: constants.py.in ../Makefile ../Make.defs Makefile
	sed -e s,@version@,$(VERSION),g \
	$< > $@

install: all install-subdirs pyfiles-install default-install
	install constants.py $(DESTDIR)$(rbuilddir)/constants.py
	$(PYTHON) -c "import compileall; compileall.compile_dir('$(DESTDIR)$(rbuilddir)', ddir='$(rbuilddir)', quiet=1)"
	$(PYTHON) -OO -c "import compileall; compileall.compile_dir('$(DESTDIR)$(rbuilddir)', ddir='$(rbuilddir)', quiet=1)"

dist: default-dist

clean: clean-subdirs default-clean
	rm -f constants.py

include ../Make.rules
include ../Make.defs
