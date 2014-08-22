# -*- coding: utf-8 -*-
##j## BOF

"""
direct PAS
Python Application Services
----------------------------------------------------------------------------
(C) direct Netware Group - All rights reserved
https://www.direct-netware.de/redirect?pas;http;discuss

The following license agreement remains valid unless any additions or
changes are being made by direct Netware Group in a written form.

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc.,
59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
----------------------------------------------------------------------------
https://www.direct-netware.de/redirect?licenses;gpl
----------------------------------------------------------------------------
#echo(pasHttpDiscussVersion)#
#echo(__FILEPATH__)#
"""

from dNG.pas.data.settings import Settings
from dNG.pas.data.translatable_exception import TranslatableException
from dNG.pas.database.connection import Connection
from dNG.pas.module.controller.abstract_http import AbstractHttp as AbstractHttpController

class Module(AbstractHttpController):
#
	"""
Module for "discuss"

:author:     direct Netware Group
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    https://www.direct-netware.de/redirect?licenses;gpl
             GNU General Public License 2
	"""

	def __init__(self):
	#
		"""
Constructor __init__(Module)

:since: v0.1.00
		"""

		AbstractHttpController.__init__(self)

		Settings.read_file("{0}/settings/pas_http_discuss.json".format(Settings.get("path_data")))
	#

	def execute(self):
	#
		"""
Execute the requested action.

:since: v0.1.00
		"""

		# pylint: disable=broad-except

		try: database = Connection.get_instance()
		except Exception as handled_exception:
		#
			if (self.log_handler != None): self.log_handler.error(handled_exception, context = "pas_http_site")
			raise TranslatableException("core_database_error", _exception = handled_exception)
		#

		with database: return AbstractHttpController.execute(self)
	#
#

##j## EOF