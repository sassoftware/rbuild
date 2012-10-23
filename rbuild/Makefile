#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


python_files = $(wildcard *.py)

SUBDIRS = internal pluginapi facade productstore

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
