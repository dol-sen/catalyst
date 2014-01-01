
# Maintained in full by:
# Catalyst Team <catalyst@gentoo.org>
# Release Engineering Team <releng@gentoo.org>

'''
compress.py

Utility class to hold and handle all possible compression
and de-compression of files using native linux utilities.
Including rsync transfers.

'''


import os
from collections import namedtuple

from support import cmd


DEFINITION_FIELDS = ["func", "cmd", "args", "id", "extension"]
DEFINTITION_TYPES = [ str,    str,   list,   str,  list]

DEFINITION_HELP = \
'''The definition entries are to follow the the definition_types
with the exception of the first entry "Type" which is a mode identifier
for use in the class as a type ID and printable output string.

Definiton entries are composed of the following:
    access key: list of definition fields values.
    eg:
    "tar"       :["_common", "tar", ["-cpf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "TAR", ["tar"]],
    access key  : list of DEFINITION_FIELDS
                 ["func", <== the class function to use to run the external utility with
                             "cmd", <==  the external utility command
                                     "args", <==  a list of the arguments to pass to the utility
                                                                                                  "id", <== ID string that identifies the utility
                                                                                                        "extension"], <== the list of file extensions this command handles

Available named string variables that will be substituted with the passed in
values during run time:
"%(filename)s"      filename parameter to pass to the utility
"%(basedir)s"       the base source directory where source originates from
"%(source)s"        the file or directory being acted upon
"%(destination)s"   the destination file or directory
"%(arch)s"          the arch filter to pass in  ie. Available filters: x86, arm, armthumb, powerpc, sparc, ia64
'''


COMPRESS_DEFINITIONS = {
	"Type"      :["Compression", "Compression definitions loaded"],
	"rsync"     :["rsync", "rsync", ["-a", "--delete", "%(source)s",  "%(destination)s"], "RSYNC", None],
	"lbzip2"    :["_common", "tar", ["-I", "lbzip2", "-cf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "LBZIP2", ["tar.bz2"]],
	"tbz2"      :["_common", "tar", ["-I", "lbzip2", "-cf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "LBZIP2", ["tbz2"]],
	"bzip2"     :["_common", "tar", ["-cpjf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "BZIP2", ["tar.bz2"]],
	"tar"       :["_common", "tar", ["-cpf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "TAR", ["tar"]],
	"xz"        :["_common", "tar", ["-cpJf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "XZ", ["tar.xz"]],
	"pixz"      :["_common", "tar", ["-I", "pixz", "-cpf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "PIXZ", ["tar.xz"]],
	"gzip"      :["_common", "tar", ["-cpzf", "%(filename)s", "-C", "%(basedir)s", "%(source)s"], "GZIP", ["tar.gz"]],
	"squashfs"  :["_common", "mksquashfs", ["%(source)s", "%(destination)s", "-comp", "xz", "-Xbcj", "%(arch)s", "-b", "1M"], "SQUASHFS", ["squashfs", "sfs"]],
	}


DECOMPRESS_DEFINITIONS = {
	"Type"      :["Decompression", "Decompression definitions loaded"],
	"rsync"     :["rsync", "rsync", ["-a", "--delete", "%(source)s", "%(destination)s"], "RSYNC", None],
	"lbzip2"    :["_common", "tar", ["-I", "lbzip2", "-xpf", "%(source)s", "-C", "%(destination)s"], "LBZIP2", ["bz2", "tar.bz2", "tbz2"]],
	"bzip2"     :["_common", "tar", ["-xpf", "%(source)s", "-C", "%(destination)s"], "BZIP2", ["bz2", "tar.bz2", "tbz2"]],
	"tar"       :["_common", "tar", ["-xpf", "%(source)s", "-C", "%(destination)s"], "TAR", ["tar"]],
	"xz"        :["_common", "tar", ["-xpf", "%(source)s", "-C", "%(destination)s"], "XZ", ["xz", "tar.xz"]],
	"pixz"      :["_common", "tar", ["-I", "pixz", "-xpf", "%(source)s", "-C", "%(destination)s"], "PIXZ", ["xz", "tar.xz"]],
	"gzip"      :["_common", "tar", ["-xpzf", "%(source)s", "-C", "%(destination)s"], "GZIP", ["gz", "tar.gz"]],
	"squashfs"  :["_common", "unsquashfs", ["-d", "%(destination)s", "%(source)s"], "SQUASHFS", ["squashfs", "sfs"]],
	}


'''Configure this here in case it is ever changed.
This is the only edit point required then.'''
EXTENSION_SEPARATOR = '.'


def create_classes(definitions, fields):
	'''This function dynamically creates the namedtuple classes which are
	used for the information they contain in a consistent manner.

	@parm definitions: dict, of (de)compressor definitions
		see DEFINITION_FIELDS and DEFINTITION_TYPES defined in this
		library.
	@param fields: list of the field names to create
	@return class_map: dictionary of key: namedtuple class instance
	'''
	class_map = {}
	for name in list(definitions):
		# create the namedtuple class instance
		obj = namedtuple(name, fields)
		# reduce memory used by limiting it to the predefined fields variables
		obj.__slots__ = ()
		# now add the instance to our map
		class_map[name] = obj._make(definitions[name])
	del obj
	return class_map


class CompressMap(object):
	'''Class for handling
	Catalyst's compression & decompression of archives'''

	'''fields: list of ordered field names for the (de)compression functions'''
	fields = DEFINITION_FIELDS[:]


	def __init__(self, definitions=None, env=None,
			default_mode=None, separator=EXTENSION_SEPARATOR):
		'''Class init

		@param compress_mode: boolean, defaults to True
			describes compression or de-compression definitions loaded
		@param definitions: dictionary of
			Key:[function, cmd, cmd_args, Print/id string, extension]
		@param env: environment to pass to the cmd subprocess
		'''
		if definitions is None:
			definitions = {}
			self.loaded_type = ["None", "No definitions loaded"]
		else:
			self.loaded_type = definitions.pop('Type')
		self.env = env or {}
		self.mode_error = self.loaded_type[0] + \
			" Error: No mode was passed in or automatically detected"
		self._map = {}
		self.extension_separator = separator
		# set some defaults depending on what is being loaded
		if self.loaded_type[0] in ['Compression']:
			self.mode = default_mode or 'tbz2'
			self.compress = self._compress
			self.extract = None
		else:
			self.mode = default_mode or 'auto'
			self.compress = None
			self.extract = self._extract
		# create the (de)compression definition namedtuple classes
		self._map = self.create_classes(definitions, self.fields)


	def _compress(self, infodict=None, filename='', source=None,
			basedir='.', mode=None, auto_extension=False, fatal=True):
		'''Compression function

		@param infodict: optional dictionary of the next 4 parameters.
		@param filename: optional string, name ot the file to make
		@param source: optional string, path to a directory
		@param destination: optional string, path a directory
		@param mode: string, optional mode to use to (de)compress with
		@param auto_extension: boolean, optional, enables or disables
			adding the normaL file extension defined by the mode used.
			defaults to False
		@param fatal: boolean, pass through variable
			passed to the command subprocess handler
		@return boolean
		'''
		if not infodict:
			infodict = self.create_infodict(source, None,
				basedir, filename, mode or self.mode, auto_extension)
		if not infodict['mode']:
			print self.mode_error
			return False
		if auto_extension:
			infodict['auto-ext'] = True
		return self._run(infodict, fatal=fatal)


	def _extract(self, infodict=None, source=None, destination=None,
			mode=None, fatal=True):
		'''De-compression function

		@param infodict: optional dictionary of the next 3 parameters.
		@param source: optional string, path to a directory
		@param destination: optional string, path a directory
		@param mode: string, optional mode to use to (de)compress with
		@param fatal: boolean, pass through variable
			passed to the command subprocess handler
		@return boolean
		'''
		if self.loaded_type[0] not in ["Decompression"]:
			return False
		if not infodict:
			infodict = self.create_infodict(source, destination, mode=mode)
		if infodict['mode'] in [None]:
			infodict['mode'] = self.mode or 'auto'
		if infodict['mode'] in ['auto']:
			infodict['mode'] = self.get_extension(infodict['source'])
			if not infodict['mode']:
				print self.mode_error
				return False
		return self._run(infodict, fatal=fatal)


	def _run(self, infodict, fatal=True):
		'''Internal function that runs the designated function

		@param infodict: dictionary of the next 3 parameters.
		@param fatal: boolean, pass through variable
			passed to the command subprocess handler
		@return boolean
		'''
		if not self.is_supported(infodict['mode']):
			print "mode: %s is not supported in the current %s definitions" \
				% (infodict['mode'], self.loaded_type[1])
			return False
		try:
			func = getattr(self, self._map[infodict['mode']].func)
			success = func(infodict, fatal)
		except AttributeError:
			print "FAILED to find function '%s'" % str(self._map[infodict['mode']].func)
			return False
		#except Exception as e:
			#msg = "Error performing %s %s, " % (mode, self.loaded_type[0]) + \
				#"is the appropriate utility installed on your system?"
			#print msg
			#print "Exception:", e
			#return False
		return success


	def get_extension(self, source):
		'''Extracts the file extension string from the source file

		@param source: string, file path of the file to determine
		@return string: file type extension of the source file
		'''
		return os.path.splitext(source)[1]


	def rsync(self, infodict=None, source=None, destination=None,
			mode=None, fatal=True):
		'''Convienience function. Performs an rsync transfer

		@param infodict: dict as returned by this class's create_infodict()
		@param source: optional string, path to a directory
		@param destination: optional string, path a directory
		@param mode: string, optional mode to use to (de)compress with
		@param fatal: boolean, pass through variable
			passed to the command subprocess handler
		@return boolean
		'''
		if not infodict:
			if not mode:
				mode = 'rsync'
			infodict = self.create_infodict(source, destination, mode=mode)
		return self._run(infodict, fatal=fatal)


	def _common(self, infodict, fatal=True):
		'''Internal function.  Performs commonly supported
		compression or decompression commands.

		@param infodict: dict as returned by this class's create_infodict()
		@param fatal: boolean, pass through variable
			passed to the command subprocess handler
		@return boolean
		'''
		if not infodict['mode'] or not self.is_supported(infodict['mode']):
			print "ERROR: CompressMap; %s mode: %s not correctly set!" \
				% (self.loaded_type[0], infodict['mode'])
			return False

		#Avoid modifying the source dictionary
		cmdinfo = infodict.copy()

		# obtain the pointer to the mode class to use
		cmdlist = self._map[cmdinfo['mode']]

		# for compression, add the file extension if enabled
		if cmdinfo['auto-ext']:
			cmdinfo['filename'] += self.extension_separator + \
				self.extension(cmdinfo["mode"])

		# Do the string substitution
		opts = ' '.join(cmdlist.args) %(cmdinfo)
		args = ' '.join([cmdlist.cmd, opts])

		# now run the (de)compressor command in a subprocess
		# return it's success/fail return value
		return cmd(args, cmdlist.id, env=self.env, fatal=fatal)


	def create_infodict(self, source, destination=None, basedir=None,
			filename='', mode=None, auto_extension=False, arch=None):
		'''Puts the source and destination paths into a dictionary
		for use in string substitution in the defintions
		%(source) and %(destination) fields embedded into the commands

		@param source: string, path to a directory
		@param destination: string, path a directory
		@param basedir: optional string, path a directory
		@param filename: optional string
		@param mode: string, optional mode to use to (de)compress with
		@param auto_extension: boolean, optional, enables or disables
			adding the normaL file extension defined by the mode used.
			defaults to False
		@return dict:
		'''
		return {
			'source': source,
			'destination': destination,
			'basedir': basedir,
			'filename': filename,
			'arch': arch,
			'mode': mode or self.mode,
			'auto-ext': auto_extension,
			}


	def is_supported(self, mode):
		'''Truth function to test the mode desired is supported
		in the definitions loaded

		@param mode: string, mode to use to (de)compress with
		@return boolean
		'''
		return mode in list(self._map)


	@property
	def available_modes(self):
		'''Convienence function to return the available modes'''
		return list(self._map)


	def best_mode(self, prefered_mode, source):
		'''Compare the prefered_mode's extension with the source extension
		and returns the best choice

		@param prefered_mode: string
		@param source: string, path the the source file
		@return string: best mode to use for the extraction
		'''
		ext = self.get_extension(source)
		if ext in self._map[prefered_mode].extension:
			return prefered_mode
		return ext


	def extension(self, mode, all_extensions=False):
		'''Returns the predetermined extension auto-ext added
		to the filename for compression.

		@param mode: string
		@return string
		'''
		if self.is_supported(mode):
			if all_extensions:
				return self._map[mode].extension
			else: #return the first one (default)
				return self._map[mode].extension[0]
		return ''
