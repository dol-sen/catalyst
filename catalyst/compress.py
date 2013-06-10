
# Maintained in full by:
# Catalyst Team <catalyst@gentoo.org>
# Release Engineering Team <releng@gentoo.org>

'''
compress.py

Utility class to hold and handle all possible compression
and de-compression of files.  Including rsync transfers.

'''


from collections import namedtuple

from support import cmd


# fields = ["func", "cmd", "args", "id"]
compress_definitions = {
	"Type": ["Compression", "Compression definitions loaded"],
	"rsync"		:["rsync", "rsync", ["-a", "--delete", "%(source)s",  "%(destination)s"], "RSYNC"],
	"lbz2"		:["_common", "tar", ["-I", "lbzip2", "-cf", "%(filename)s", "-C", "%(destination)s", "%(source)s"], "LBZIP2"],
	"bz2"		:["_common", "tar", ["-cpjf", "%(filename)s", "-C", "%(destination)s", "%(source)s"], "BZIP2"],
	"tar"		:["_common", "tar", ["-cpf", "%(filename)s", "-C", "%(destination)s", "%(source)s"], "TAR"],
	"xz"		:["_common", "tar", ["-cpJf", "%(filename)s", "-C", "%(destination)s", "%(source)s"], "XZ"],
	"pixz"		:["_common", "tar", ["-I", "pixz", "-cpf", "%(filename)s", "-C", "%(destination)s", "%(source)s"], "PIXZ"],
	"zip"		:["_common", "tar", ["-cpzf", "%(filename)s", "-C", "%(destination)s", "%(source)s"], "GZIP"],
	}


# fields = ["func", "cmd", "args", "id"]
decompress_definitions = {
	"Type": ["Decompression", "Decompression definitions loaded"],
	"rsync"		:["rsync", "rsync", ["-a", "--delete", "%(source)s", "%(destination)s"], "RSYNC"],
	"bz2"		:["_common", "tar", ["-I", "lbzip2", "-xpf", "%(source)s", "-C", "%(destination)s"], "LBZIP2"],
	"tar"		:["_common", "tar", ["-xpf", "%(source)s", "-C", "%(destination)s"], "TAR"],
	"xz"		:["_common", "tar", ["-xpf", "%(source)s", "-C", "%(destination)s"], "XZ"],
	"pixz"		:["_common", "tar", ["-I", "pixz", "-xpf", "%(source)s", "-C", "%(destination)s"], "PIXZ"],
	"zip"		:["_common", "tar", ["-xpzf", "%(source)s", "-C", "%(destination)s"], "GZIP"],
	"gz"		:["_common", "tar", ["-xpzf", "%(source)s", "-C", "%(destination)s"], "GZIP"],
	}


extension_separator = '.'


class CompressMap(object):
	'''Class for handling
	Catalyst's compression & decompression of archives'''

	'''fields: list of ordered field names for the (de)compression functions'''
	fields = ["func", "cmd", "args", "id"]


	def __init__(self, definitions=None, env=None, separator=extension_separator):
		'''Class init

		@param compress_mode: boolean, defaults to True
			describes compression or de-compression definitions loaded
		@param definitions: dictionary of Key:[function, cmd, cmd_args, Print/id string]
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

		# create the (de)compression definition namedtuple classes
		for name in list(definitions):
			obj = namedtuple(name, self.fields)
			obj.__slots__ = ()
			self._map[name] = obj._make(definitions[name])
		del obj


	def compress(self, infodict=None, filename='', source=None,
			target_dir=None, mode=None, auto_extension=False, fatal=True):
		'''Compression function

		@param infodict: optional dictionary of the next 4 parameters.
		@param filename: optional string, name ot the file to make
		@param source: optional string, path to a directory
		@param destination: optional string, path a directory
		@param mode: string, optional mode to use to (de)compress with
		@return boolean
		'''
		if self.loaded_type[0] not in ["Compression"]:
			return False
		if not infodict:
			infodict = self.create_infodict(source, None,
				basedir, filename, mode or self.mode, auto_extension)
		if not infodict['mode']:
			print self.mode_error
			return False
		if infodict['auto-ext'] or auto_extension:
			infodict['filename'] += self.extension_separator + infodict['mode']
		return self._run(infodict, fatal=fatal)


	def extract(self, infodict=None, source=None, destination=None,
			mode=None, fatal=True):
		'''De-compression function

		@param infodict: optional dictionary of the next 3 parameters.
		@param source: optional string, path to a directory
		@param destination: optional string, path a directory
		@param mode: string, optional mode to use to (de)compress with
		@return boolean
		'''
		if self.loaded_type[0] not in ["Decompression"]:
			return False
		if not infodict:
			infodict = self.create_infodict(source, destination, mode=mode)
		if infodict['mode'] in ['auto', None]:
			infodict['mode'] = self.get_extension(infodict['source'])
			if not infodict['mode']:
				print self.mode_error
				return False
		return self._run(infodict, fatal=fatal)


	def _run(self, infodict, fatal=True):
		'''Internal function that runs the designated function

		@param source: string, path to a directory or file
		@param destination: string, path a directoy or file
		@param mode; string, desired method to perform the
			compression or transfer
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
			print "FAILED to find function %s" % self._map[infodict['mode']]
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
		if self.extension_separator not in source:
			return None
		return source.rsplit(self.extension_separator, 1)[1]


	def rsync(self, infodict=None, source=None, destination=None,
			mode=None, fatal=True):
		'''Convienience function. Performs an rsync transfer

		@param infodict: optional dictionary of the next 3 parameters.
		@param source: optional string, path to a directory
		@param destination: optional string, path a directory
		@param mode: string, optional mode to use to (de)compress with
		@return boolean
		'''
		if not infodict:
			if not mode:
				mode = 'rsync'
			infodict = self.create_infodict(source, destination, mode=mode)
		return self._run(infodict, fatal=fatal)


	def _common(self, infodict, fatal=True):
		'''Internal function.  Performs commonly supported
		compression or decompression.

		@param files: dict as returned by this class's pair_files()
		@param mode: string, mode to use to (de)compress with
		@return boolean
		'''
		if not infodict['mode']:
			print "ERROR: CompressMap; %s mode not set!" % self.loaded_type[0]
			return False
		cmdlist = self._map[infodict['mode']]
		# Do the string substitution
		opts = ' '.join(cmdlist.args) %(infodict)
		args = ' '.join([cmdlist.cmd, opts])

		return cmd(args, cmdlist.id, env=self.env, fatal=fatal)


	@staticmethod
	def create_infodict(source, destination, filename='', mode=None,
			auto_extension=True):
		'''Puts the source and destination paths into a dictionary
		for use in string substitution in the defintions
		%(source) and %(destination) fields embedded into the commands

		@param source: string, path to a directory
		@param destination: string, path a directory
		@param filename: optional string
		@return dict:
		'''
		return {
			'source': source,
			'destination': destination,
			'filename': filename,
			'mode': mode,
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
