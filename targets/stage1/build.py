#!/usr/bin/python
# Copyright 1999-2004 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo/src/catalyst/targets/stage1/build.py,v 1.1 2004/08/02 23:23:34 zhen Exp $

import portage

# this loads files from the profiles ...
# wrap it here to take care of the different
# ways portage handles stacked profiles
def scan_profile(file):
	if "grab_stacked" in dir(portage):
		return portage.grab_stacked(file, portage.settings.profiles, portage.grabfile, incremental_lines=1);
	else:
		return portage.stack_lists( portage.grab_multiple(file, portage.settings.profiles, portage.grabfile), incremental=1);

# loaded the stacked packages / packages.build files
pkgs = scan_profile("packages")
buildpkgs = scan_profile("packages.build")

# go through the packages list and strip off all the
# crap to get just the <category>/<package> ... then
# search the buildpkg list for it ... if it's found,
# we replace the buildpkg item with the one in the
# system profile (it may have <,>,=,etc... operators
# and version numbers)
for idx in range(0, len(pkgs)):
	try:
		bidx = buildpkgs.index(portage.dep_getkey(pkgs[idx]))
		buildpkgs[bidx] = pkgs[idx]
		if buildpkgs[bidx][0:1] == "*":
			buildpkgs[bidx] = buildpkgs[bidx][1:]
	except: pass

for b in buildpkgs: print b