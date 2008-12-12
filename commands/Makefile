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

TOPDIR=..

bin_files = \
	rbuild rbuilder

extra_dist = Makefile rbuild-wrapper rbuilder-wrapper

dist_files = $(bin_files) $(extra_dist) $(sbin_files)

all: default-all 
	mkdir -p $(TOPDIR)/bin
	install -m755 rbuild-wrapper $(TOPDIR)/bin/rbuild-wrapper
	install -m755 rbuilder-wrapper $(TOPDIR)/bin/rbuilder-wrapper
	for f in $(bin_files) $(sbin_files); do \
		ln -sf rbuild-wrapper $(TOPDIR)/bin/$$f; \
		ln -sf rbuilder-wrapper $(TOPDIR)/bin/$$f; \
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
