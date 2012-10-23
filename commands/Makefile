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


TOPDIR=..

bin_files = rbuild

extra_dist = Makefile rbuild-wrapper


all: default-all 
	mkdir -p $(TOPDIR)/bin
	install -m755 rbuild-wrapper $(TOPDIR)/bin/rbuild-wrapper
	for f in $(bin_files) $(sbin_files); do \
		ln -sf rbuild-wrapper $(TOPDIR)/bin/$$f; \
	done

install-mkdirs:
	mkdir -p $(DESTDIR)$(bindir)

install: install-mkdirs
	for f in $(bin_files); do \
		install -m755 $$f $(DESTDIR)$(bindir)/$$f; \
	done
	for f in $(sbin_files); do \
		install -m755 $$f $(DESTDIR)$(sbindir)/$$f; \
	done

dist: default-dist

clean: default-clean
	rm -rf $(TOPDIR)/bin

include $(TOPDIR)/Make.rules
include $(TOPDIR)/Make.defs
