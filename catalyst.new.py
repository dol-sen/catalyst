#!/usr/bin/python
# Copyright 1999-2004 Gentoo Technologies, Inc.
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo/src/catalyst/Attic/catalyst.new.py,v 1.1 2004/07/07 01:46:31 zhen Exp $

# Maintained in full by John Davis <zhen@gentoo.org>

import os,sys,imp,string,getopt,types

__maintainer__="John Davis <zhen@gentoo.org>"
__version__="1.0.9"

conf_values={}

def usage():
	print "Usage catalyst [-f file] [variable=value...]"
	print " -h --help		print this help message"
	print " -v --version		display version information"
	print " -d --debug		enable debugging"
	print " -c --config		use specified configuration file"
	print " -C --cli		catalyst commandline"
	print " -f --file		read specfile"
	print " -V --verbose		verbose output"

def version():
	print "Gentoo Catalyst, version "+__version__
	print "Copyright 2003-2004 The Gentoo Foundation"
	print "Distributed under the GNU General Public License version 2\n"
	

def parse_config(myconfig):
	# search a couple of different areas for the main config file
	myconf={}
	config_file=""

	confdefaults={ "storedir":"/var/tmp/catalyst",\
		"sharedir":"/usr/share/catalyst","distdir":"/usr/portage/distfiles",\
		"portdir":"/usr/portage","options":""}
		
	# first, try the one passed (presumably from the cmdline)
	if myconfig:
		if os.path.exists(myconfig):
			print "Using command line specified Catalyst configuration file, "+myconfig
			config_file=myconfig

		else:
			print "!!! catalyst: Could not use specified configuration file "+\
				myconfig
			sys.exit(1)
	
	# next, try the default location
	elif os.path.exists("/etc/catalyst/catalyst.conf"):
		print "Using default Catalyst configuration file, /etc/catalyst/catalyst.conf"
		config_file="/etc/catalyst/catalyst.conf"
	
	# can't find a config file (we are screwed), so bail out
	else:
		print "!!! catalyst: Could not find a suitable configuration file"
		sys.exit(1)

	# now, try and parse the config file "config_file"
	try:
		execfile(config_file, myconf, myconf)
	
	except:
		print "!!! catalyst: Unable to parse configuration file, "+myconfig
		sys.exit(1)
	
	# now, load up the values into conf_values so that we can use them
	for x in confdefaults.keys():
		if myconf.has_key(x):
			print "Setting",x,"to config file value \""+myconf[x]+"\""
			conf_values[x]=myconf[x]
		else:
			print "Setting",x,"to default value \""+confdefaults[x]+"\""
			conf_values[x]=confdefaults[x]

	# parse out the rest of the options from the config file
	if "ccache" in string.split(conf_values["options"]):
		print "Compiler cache support enabled."
		conf_values["CCACHE"]="1"

	if "pkgcache" in string.split(conf_values["options"]):
		print "Package cache support enabled."
		conf_values["PKGCACHE"]="1"
	
	if "distcc" in string.split(conf_values["options"]):
		print "Distcc support enabled."
		conf_values["DISTCC"]="1"

	if "autoresume" in string.split(conf_values["options"]):
		print "Autoresuming support enabled."
		conf_values["AUTORESUME"]="1"

	if myconf.has_key("envscript"):
		print "Envscript support enabled."
		conf_values["ENVSCRIPT"]=myconf["envscript"]

def import_modules():
	# import catalyst's own modules (i.e. catalyst_support and the arch modules)
	targetmap={}
	
	try:
		for x in required_build_targets:
			try:
				fh=open(conf_values["sharedir"]+"/modules/"+x+".py")
				module=imp.load_module(x,fh,"modules/"+x+".py",(".py","r",imp.PY_SOURCE))
				fh.close()
        	
			except IOError:
				raise CatalystError,"Can't find "+x+".py plugin in "+\
					conf_values.settings["sharedir"]+"/modules/"

		for x in valid_build_targets:
			try:
				fh=open(conf_values["sharedir"]+"/modules/"+x+".py")
				module=imp.load_module(x,fh,"modules/"+x+".py",(".py","r",imp.PY_SOURCE))
				module.register(targetmap)
				fh.close()
        	
			except IOError:
				raise CatalystError,"Can't find "+x+".py plugin in "+\
					conf_values.settings["sharedir"]+"/modules/"

	except ImportError:
		print "!!! catalyst: python modules not found in "+\
			conf_values["sharedir"]+"/modules; exiting."
		sys.exit(1)

	return targetmap

def do_spec(myspecfile):
	try:
		addlargs=read_spec(myspecfile)
	except:
		sys.exit(1)
		
	return addlargs	
		
def build_target(addlargs, targetmap):
	try:
		if not targetmap.has_key(addlargs["target"]):
			raise CatalystError,"Target \""+addlargs["target"]+"\" not available."
		
		mytarget=targetmap[addlargs["target"]](conf_values, addlargs)
		mytarget.run()

	except CatalystError:
		sys.exit(1)
	
if __name__ == "__main__":
	targetmap={}
	
	version()
	if os.getuid() != 0:
		# catalyst cannot be run as a normal user due to chroots, mounts, etc
		print "!!! catalyst: This script requires root privileges to operate"
		sys.exit(2)

	# we need some options in order to work correctly
	if len(sys.argv) < 2:
		usage()
		sys.exit(2)

	# parse out the command line arguments
	try:
		opts,args = getopt.getopt(sys.argv[1:], "hvdc:C:f:V", ["help", "version", "debug",\
			"config=", "commandline=", "file=", "verbose"])
	
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	
	# defaults for commandline opts
	debug=False
	verbose=False
	myconfig=""
	myspecfile=""
	mycmdline=[]

	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit(2)
		
		if o in ("-v", "--version"):
			print "Catalyst version "+__version__
			sys.exit(2)

		if o in ("-d", "--debug"):
			debug=True

		if o in ("-c", "--config"):
			myconfig=a

		# needs some work
		if o in ("-C", "--cli"):
			if type(a)==types.StringType:
				mycmdline=[a]
			else:
				mycmdline=a
		
		if o in ("-f", "--file"):
			myspecfile=a
			
		if o in ("-V", "--verbose"):
			verbose=True
	
	# import configuration file and import our main module using those settings
	parse_config(myconfig)
	sys.path.append(conf_values["sharedir"]+"/modules")
	from catalyst_support import *
		
	# import the rest of the catalyst modules
	targetmap=import_modules()

	if myspecfile:
		addlargs=do_spec(myspecfile)

	# everything is setup, so the build is a go
	try:
		build_target(addlargs, targetmap)
	except:
		print "!!! catalyst: could not complete build"
