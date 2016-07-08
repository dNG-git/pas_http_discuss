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

from math import ceil

from dNG.data.discuss.list import List as _List
from dNG.data.hookable_settings import HookableSettings
from dNG.data.http.translatable_error import TranslatableError
from dNG.data.xhtml.link import Link
from dNG.data.xhtml.page_links_renderer import PageLinksRenderer
from dNG.data.xhtml.oset.file_parser import FileParser
from dNG.runtime.value_exception import ValueException

from .module import Module

class List(Module):
#
	"""
"List" creates a list of documents of different types.

:author:     direct Netware Group et al.
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    https://www.direct-netware.de/redirect?licenses;gpl
             GNU General Public License 2
	"""

	def execute_render_hybrid_subs(self):
	#
		"""
Action for "render_hybrid_subs"

:since: v0.1.00
		"""

		if (self._is_primary_action()): raise TranslatableError("core_access_denied", 403)

		if ("id" in self.context): raise ValueException("Missing discuss list ID to render")

		self._render(self.context['id'])
	#

	def execute_render_subs(self):
	#
		"""
Action for "render_subs"

:since: v0.1.00
		"""

		if (self._is_primary_action()): raise TranslatableError("core_access_denied", 403)

		if ("id" not in self.context): raise ValueException("Missing discuss list ID to render")

		_id = self.context['id']

		hookable_settings = HookableSettings("dNG.pas.http.discuss.List.getLimit",
		                                     id = _id
		                                    )

		limit = hookable_settings.get("pas_http_discuss_list_limit", 20)

		self._render(_id, limit)
	#

	def _render(self, _id, limit = -1):
	#
		"""
Subs renderer

:since: v0.1.00
		"""

		_list = _List.load_id(_id)
		list_data = _list.get_data_attributes("sub_entries")

		if (limit < 0):
		#
			page = 1
			pages = 1

			offset = 0
		#
		else:
		#
			page = self.context.get("page", 1)
			pages = (1 if (list_data['sub_entries'] == 0) else ceil(float(list_data['sub_entries']) / limit))

			offset = (0 if (page < 1 or page > pages) else (page - 1) * limit)
		#

		if ("sort_definition" in self.context): _list.set_sort_definition(self.context['sort_definition'])

		page_link_renderer = PageLinksRenderer({ "__request__": True }, page, pages)
		page_link_renderer.set_dsd_page_key("dpage")
		rendered_links = page_link_renderer.render()

		rendered_content = rendered_links
		for sub_entry in _list.get_sub_entries(offset, limit): rendered_content += self._render_entry(sub_entry)
		rendered_content += "\n" + rendered_links

		self.set_action_result(rendered_content)
	#

	def _render_entry(self, entry):
	#
		"""
Renders the list.

:return: (str) Entry XHTML
:since:  v0.1.01
		"""

		entry_data = entry.get_data_attributes("id", "title", "time_sortable", "sub_entries", "sub_entries_type", "author_id", "author_ip", "time_published", "entry_type", "description")

		content = { "id": entry_data['id'],
		            "title": entry_data['title'],
		            "link": Link().build_url(Link.TYPE_RELATIVE_URL, { "m": "discuss", "dsd": { "dlid": entry_data['id'] } }),
		            "description": entry_data['description'],
		            "topics": entry.get_total_topics_count(),
		            "posts": entry.get_total_posts_count()
		          }

		latest_timestamp = entry.get_latest_timestamp()

		if (latest_timestamp > 0):
		#
			author_id = entry.get_latest_author_id()

			content['latest_timestamp'] = latest_timestamp
			content['latest_topic_id'] = entry.get_latest_topic_id()
			if (author_id is not None): content['latest_author'] = { "id": author_id }
			content['latest_preview'] = entry.get_latest_preview()
		#

		parser = FileParser()
		parser.set_oset(self.response.get_oset())
		_return = parser.render("discuss.list_entry", content)

		return _return
	#
#

##j## EOF