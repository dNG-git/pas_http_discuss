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

from dNG.pas.data.hookable_settings import HookableSettings
from dNG.pas.data.discuss.topic import Topic
from dNG.pas.data.http.translatable_exception import TranslatableException
from dNG.pas.data.text.l10n import L10n
from dNG.pas.data.xhtml.link import Link
from dNG.pas.data.xhtml.page_links_renderer import PageLinksRenderer
from dNG.pas.data.xhtml.oset.file_parser import FileParser
from .module import Module

class PostList(Module):
#
	"""
"PostList" creates a list of posts.

:author:     direct Netware Group
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    https://www.direct-netware.de/redirect?licenses;gpl
             GNU General Public License 2
	"""

	def execute_render(self):
	#
		"""
Action for "render"

:since: v0.1.00
		"""

		if ("id" in self.context): self._render(self.context['id'])
		else: raise TranslatableException("core_unknown_error", "Missing topic ID to render")
	#

	def _render(self, _id):
	#
		"""
List renderer

:since: v0.1.00
		"""

		topic = Topic.load_id(_id)
		posts_count = topic.get_posts_count()

		hookable_settings = HookableSettings("dNG.pas.http.discuss.PostList.getLimit",
		                                     id = _id
		                                    )

		limit = hookable_settings.get("pas_http_discuss_post_list_limit", 12)

		page = (self.context['page'] if ("page" in self.context) else 1)
		pages = (1 if (posts_count == 0) else ceil(float(posts_count) / limit))

		offset = (0 if (page < 1 or page > pages) else (page - 1) * limit)

		if ("sort_definition" in self.context): topic.set_sort_definition(self.context['sort_definition'])

		page_link_renderer = PageLinksRenderer({ "__request__": True }, page, pages)
		page_link_renderer.set_dsd_page_key("dpage")
		rendered_links = page_link_renderer.render()

		rendered_content = rendered_links
		for post in topic.get_posts(offset, limit): rendered_content += self._render_post(topic, post)
		rendered_content += "\n" + rendered_links

		self.set_action_result(rendered_content)
	#

	def _render_post(self, topic, post):
	#
		"""
Renders the post.

:return: (str) Post XHTML
:since:  v0.1.01
		"""

		post_data = post.get_data_attributes("id",
		                                     "title",
		                                     "time_sortable",
		                                     "sub_entries",
		                                     "sub_entries_type",
		                                     "author_id",
		                                     "author_ip",
		                                     "time_published",
		                                     "preserve_space",
		                                     "content"
		                                    )

		content = { "id": post_data['id'],
		            "title": post_data['title'],
		            "link": Link().build_url(Link.TYPE_RELATIVE, { "m": "discuss", "dsd": { "dpid": post_data['id'] } }),
		            "author_bar": { "id": post_data['author_id'], "ip": post_data['author_ip'], "time_published": post_data['time_published'] },
		            "time_published": post_data['time_published'],
		            "content": post_data['content'],
		            "preserve_space": post_data['preserve_space']
		          }

		options = [ ]
		session = self.request.get_session()

		if (post.is_writable_for_session_user(session)):
		#
			options.append({ "title": L10n.get("pas_http_discuss_post_edit"),
			                 "type": (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			                 "parameters": { "m": "discuss",
			                                 "s": "post",
			                                 "a": "edit",
			                                 "dsd": { "dpid": post_data['id'] }
			                               }
			               })
		#

		if (topic.is_writable_for_session_user(session)):
		#
			options.append({ "title": L10n.get("pas_http_discuss_post_reply"),
			                 "type": (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			                 "parameters": { "m": "discuss",
			                                 "s": "post",
			                                 "a": "reply",
			                                 "dsd": { "dpid": post_data['id'] }
			                               }
			               })
		#

		if (len(options) > 0): content['options'] = { "entries": options }
		if (post_data['time_published'] != post_data['time_sortable']): content['time_updated'] = post_data['time_sortable']

		parser = FileParser()
		parser.set_oset(self.response.get_oset())
		_return = parser.render("discuss.list_post", content)

		return _return
	#
#

##j## EOF