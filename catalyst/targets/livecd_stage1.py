"""
LiveCD stage1 target
"""
# NOTE: That^^ docstring has influence catalyst-spec(5) man page generation.

import os
import types
import string


from catalyst.support import (normpath,
	touch, cmd)
from catalyst.fileops import ensure_dirs

from catalyst.base.stagebase import StageBase


class livecd_stage1(StageBase):
	"""
	Builder class for LiveCD stage1.
	"""
	def __init__(self,spec,addlargs):
		self.required_values=["livecd/packages"]
		self.valid_values=self.required_values[:]

		self.valid_values.extend(["livecd/use"])
		StageBase.__init__(self,spec,addlargs)

	def set_action_sequence(self):
		self.settings["action_sequence"]=["unpack","unpack_snapshot",\
					"config_profile_link","setup_confdir","portage_overlay",\
					"bind","chroot_setup","setup_environment","build_packages",\
					"unbind", "clean","clear_autoresume"]

	def set_target_path(self):
		self.settings["target_path"]=normpath(self.settings["storedir"]+"/builds/"+self.settings["target_subpath"])
		if "autoresume" in self.settings["options"] \
			and self.resume.is_enabled("setup_target_path"):
				print "Resume point detected, skipping target path setup operation..."
		else:
			# first clean up any existing target stuff
			if os.path.exists(self.settings["target_path"]):
				cmd("rm -rf "+self.settings["target_path"],\
					"Could not remove existing directory: "+self.settings["target_path"],env=self.env)
				self.resume.enable("setup_target_path")
			ensure_dirs(self.settings["target_path"])

	def set_spec_prefix(self):
		self.settings["spec_prefix"]="livecd"

	def set_use(self):
		StageBase.set_use(self)
		if "use" in self.settings:
			self.settings["use"].append("livecd")
			if "BINDIST" in self.settings:
				self.settings["use"].append("bindist")
		else:
			self.settings["use"]=["livecd"]
			if "BINDIST" in self.settings:
				self.settings["use"].append("bindist")

	def set_packages(self):
		StageBase.set_packages(self)
		if self.settings["spec_prefix"]+"/packages" in self.settings:
			if type(self.settings[self.settings["spec_prefix"]+"/packages"]) == types.StringType:
				self.settings[self.settings["spec_prefix"]+"/packages"] = \
					self.settings[self.settings["spec_prefix"]+"/packages"].split()
		self.settings[self.settings["spec_prefix"]+"/packages"].append("app-misc/livecd-tools")

	def set_pkgcache_path(self):
		if "pkgcache_path" in self.settings:
			if type(self.settings["pkgcache_path"]) != types.StringType:
				self.settings["pkgcache_path"]=normpath(string.join(self.settings["pkgcache_path"]))
		else:
			StageBase.set_pkgcache_path(self)
