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


all: all-subdirs default-all

all-subdirs:
	for d in $(MAKEALLSUBDIRS); do make -C $$d DIR=$$d || exit 1; done

export TOPDIR = $(shell pwd)

SUBDIRS=commands rbuild plugins pylint
MAKEALLSUBDIRS=commands rbuild plugins

extra_files = \
	Make.rules 		\
	Makefile		\
	Make.defs		\
	NEWS			\
	README			\
	EULA_rBuild.txt		\
	LICENSE


.PHONY: clean dist install subdirs html

subdirs: default-subdirs

install: install-subdirs

clean: clean-subdirs default-clean

doc: html

html:
	ln -fs plugins/ rbuild_plugins
	scripts/generate_docs.sh
	rm -f rbuild_plugins

dist:
	if ! grep "^Changes in $(VERSION)" NEWS > /dev/null 2>&1; then \
		echo "no NEWS entry"; \
		exit 1; \
	fi
	$(MAKE) forcedist

show-version:
	@echo $(VERSION)

archive:
	hg archive  --exclude .hgignore -t tbz2 rbuild-$(VERSION).tar.bz2

forcedist: archive

forcetag:
	hg tag -f rbuild-$(VERSION)

tag:
	hg tag rbuild-$(VERSION)

clean: clean-subdirs default-clean

include Make.rules
include Make.defs
 
# vim: set sts=8 sw=8 noexpandtab :
