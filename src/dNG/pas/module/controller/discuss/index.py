# -*- coding: utf-8 -*-
##j## BOF

"""
direct PAS
Python Application Services
----------------------------------------------------------------------------
(C) direct Netware Group - All rights reserved
http://www.direct-netware.de/redirect.py?pas;http;discuss

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
http://www.direct-netware.de/redirect.py?licenses;gpl
----------------------------------------------------------------------------
#echo(pasHttpDiscussVersion)#
#echo(__FILEPATH__)#
"""

from dNG.pas.data.data_linker import DataLinker
from dNG.pas.data.hookable_settings import HookableSettings
from dNG.pas.data.ownable_mixin import OwnableMixin as OwnableInstance
from dNG.pas.data.settings import Settings
from dNG.pas.data.discuss.list import List
from dNG.pas.data.discuss.post import Post
from dNG.pas.data.discuss.topic import Topic
from dNG.pas.data.http.translatable_exception import TranslatableError
from dNG.pas.data.text.input_filter import InputFilter
from dNG.pas.data.text.l10n import L10n
from dNG.pas.data.xhtml.link import Link
from dNG.pas.data.xhtml.table.data_linker import DataLinker as DataLinkerTable
from dNG.pas.database.nothing_matched_exception import NothingMatchedException
from .module import Module

class Index(Module):
#
	"""
Service for "m=discuss;s=index"

:author:     direct Netware Group
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    http://www.direct-netware.de/redirect.py?licenses;gpl
             GNU General Public License 2
	"""

	def execute_index(self):
	#
		"""
Action for "index"

:since: v0.1.00
		"""

		if (self.request.is_dsd_set('dtid')): self.execute_topic()
		elif (self.request.is_dsd_set('dpid')): self.execute_post()
		elif (self.request.is_dsd_set('dlid') or Settings.is_defined("pas_http_discuss_list_default")): self.execute_list()
	#

	def execute_list(self):
	#
		"""
Action for "list"

:since: v0.1.00
		"""

		lid = InputFilter.filter_file_path(self.request.get_dsd("dlid", ""))
		page = InputFilter.filter_int(self.request.get_dsd("dpage", 1))

		if (lid == ""): lid = Settings.get("pas_http_discuss_list_default", "")

		L10n.init("pas_http_datalinker")
		L10n.init("pas_http_discuss")
		L10n.init("pas_http_subscription")

		try: _list = List.load_id(lid)
		except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_discuss_lid_invalid", 404, _exception = handled_exception)

		session = self.request.get_session()
		if (session != None): _list.set_permission_session(session)

		if (not _list.is_readable()):
		#
			if (session == None or session.get_user_profile() == None): raise TranslatableError("pas_http_discuss_lid_invalid", 404)
			else: raise TranslatableError("core_access_denied", 403)
		#

		if (self.response.is_supported("html_css_files")): self.response.add_theme_css_file("mini_default_sprite.min.css")

		is_hybrid_list = _list.is_hybrid_list()

		if (is_hybrid_list and _list.is_writable()):
		#
			Link.set_store("servicemenu",
			               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			               L10n.get("pas_http_discuss_topic_new"),
			               { "m": "discuss", "s": "topic", "a": "new", "dsd": { "dlid": lid } },
			               icon = "mini-default-option",
			               priority = 3
			              )
		#

		subscription_handler = (_list.get_subscription_handler() if (is_hybrid_list) else None)

		if (subscription_handler != None and subscription_handler.is_subscribable_for_session_user(session)):
		#
			source = "m=discuss;dsd=dlid+{0}++dpage+{1}".format(lid, page)
			subscription_dsd = { "oid": lid, "source": source }

			if (subscription_handler.is_subscribed_by_session_user(session)):
			#
				Link.set_store("servicemenu",
				               Link.TYPE_RELATIVE,
				               L10n.get("pas_http_subscription_unsubscribe"),
				               { "m": "subscription", "s": "datalinker", "a": "unsubscribe", "dsd": subscription_dsd },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#
			else:
			#
				Link.set_store("servicemenu",
				               Link.TYPE_RELATIVE,
				               L10n.get("pas_http_subscription_subscribe"),
				               { "m": "subscription", "s": "datalinker", "a": "subscribe", "dsd": subscription_dsd },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#
		#

		if (_list.is_manageable()):
		#
			Link.set_store("servicemenu",
			               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			               L10n.get("pas_http_discuss_list_manage"),
			               { "m": "discuss", "s": "list", "a": "manage", "dsd": { "dlid": lid } },
			               icon = "mini-default-option",
			               priority = 3
			              )
		#

		list_data = _list.get_data_attributes("id", "id_main", "title", "time_sortable", "sub_entries", "hybrid_list", "description", "topics", "posts")

		content = { "id": list_data['id'],
		            "title": list_data['title'],
		            "description": list_data['description'],
		            "time": list_data['time_sortable'],
		            "topics": _list.get_total_topics_count(),
		            "posts": _list.get_total_posts_count()
		          }

		if (list_data['sub_entries'] > 0):
		#
			entry_renderer_attributes = { "type": DataLinkerTable.COLUMN_RENDERER_OSET,
			                              "oset_template_name": "discuss.list_column",
			                              "oset_row_attributes": [ "id", "title", "description" ]
			                            }

			latest_post_renderer_attributes = { "type": DataLinkerTable.COLUMN_RENDERER_OSET,
			                                    "oset_template_name": "discuss.latest_post_column",
			                                    "oset_row_attributes": [ "latest_timestamp",
			                                                             "latest_topic_id",
			                                                             "latest_author_id",
			                                                             "latest_preview"
			                                                           ]
			                                  }

			table = DataLinkerTable(_list)
			table.add_column('entry', L10n.get("pas_http_discuss_list"), 30, sort_key = "title", renderer = entry_renderer_attributes)
			table.add_column('total_topics', L10n.get("pas_http_discuss_topics"), 10, renderer = { "type": DataLinkerTable.COLUMN_RENDERER_SAFE_CONTENT, "css_text_align": "center" })
			table.add_column('total_posts', L10n.get("pas_http_discuss_posts"), 10, renderer = { "type": DataLinkerTable.COLUMN_RENDERER_SAFE_CONTENT, "css_text_align": "center" })
			table.add_column('latest_post', L10n.get("pas_http_discuss_latest_post"), 50, renderer = latest_post_renderer_attributes)

			table.disable_sort("latest_post")
			table.set_limit(15)

			hookable_settings = HookableSettings("dNG.pas.http.discuss.List.getLimit",
			                                     id = list_data['id']
			                                    )

			limit = hookable_settings.get("pas_http_discuss_list_limit", 20)

			content['sub_entries'] = { "table": table }

			if (not is_hybrid_list):
			#
				content['sub_entries']['dsd_page_key'] = "dpage"
				content['sub_entries']['page'] = page
				table.set_limit(limit)
			#
		#

		if (is_hybrid_list and list_data['topics'] > 0):
		#
			topic_renderer_attributes = { "type": DataLinkerTable.COLUMN_RENDERER_OSET,
			                              "oset_template_name": "discuss.topic_column",
			                              "oset_row_attributes": [ "id", "title", "description" ]
			                            }

			latest_post_renderer_attributes = { "type": DataLinkerTable.COLUMN_RENDERER_OSET,
			                                    "oset_template_name": "discuss.last_post_column",
			                                    "oset_row_attributes": [ "time_sortable",
			                                                             "last_id_author",
			                                                             "last_preview"
			                                                           ]
			                                  }

			table = DataLinkerTable(_list)
			table.add_column('topic', L10n.get("pas_http_discuss_topic"), 40, sort_key = "title", renderer = topic_renderer_attributes)
			table.add_column('posts', L10n.get("pas_http_discuss_posts"), 10, renderer = { "type": DataLinkerTable.COLUMN_RENDERER_SAFE_CONTENT, "css_text_align": "center" })
			table.add_column('latest_post', L10n.get("pas_http_discuss_latest_post"), 50, renderer = latest_post_renderer_attributes)

			table.disable_sort("latest_post")
			table.set_limit(15)
			table.set_source_callbacks(_list.get_topics, _list.get_topics_count)

			content['topic_entries'] = { "table": table, "page": page, "dsd_page_key": "dpage" }
		#

		list_parent = _list.load_parent()

		if (list_parent != None
		    and ((not isinstance(list_parent, OwnableInstance))
		         or list_parent.is_readable_for_session_user(session)
		        )
		   ):
		#
			list_parent_data = list_parent.get_data_attributes("id", "id_main", "title")
			if (list_parent_data['id'] != lid): content['parent'] = { "id": list_parent_data['id'], "main_id": list_parent_data['id_main'], "title": list_parent_data['title'] }
		#

		self.response.init(True)
		self.response.set_expires_relative(+15)
		self.response.set_title(list_data['title'])

		self.response.add_oset_content(("discuss.hybrid_list" if (is_hybrid_list) else "discuss.list"),
		                               content
		                              )

		if (self.response.is_supported("html_canonical_url")):
		#
			parameters = { "__virtual__": "/discuss/view/list",
			               "dsd": { "dlid": lid, "dpage": page }
			             }

			self.response.set_html_canonical_url(Link().build_url(Link.TYPE_VIRTUAL_PATH, parameters))
		#
	#

	def execute_post(self):
	#
		"""
Action for "post"

:since: v0.1.00
		"""

		pid = InputFilter.filter_file_path(self.request.get_dsd("dpid", ""))

		L10n.init("pas_http_datalinker")
		L10n.init("pas_http_discuss")

		try: post = Post.load_id(pid)
		except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_discuss_pid_invalid", 404, _exception = handled_exception)

		session = self.request.get_session()
		if (session != None): post.set_permission_session(session)

		if (not post.is_readable()):
		#
			if (session == None or session.get_user_profile() == None): raise TranslatableError("pas_http_discuss_pid_invalid", 404)
			else: raise TranslatableError("core_access_denied", 403)
		#

		post_parent = post.load_main()
		is_topic = isinstance(post_parent, Topic)

		if (not isinstance(post_parent, DataLinker)): raise TranslatableError("pas_http_discuss_pid_invalid", 404)
		elif (not post_parent.is_readable_for_session_user(session)):
		#
			if (session == None or session.get_user_profile() == None): raise TranslatableError("pas_http_discuss_pid_invalid", 404)
			else: raise TranslatableError("core_access_denied", 403)
		#

		if (self.response.is_supported("html_css_files")): self.response.add_theme_css_file("mini_default_sprite.min.css")

		if (is_topic):
		#
			tid = post_parent.get_id()

			if (post_parent.is_writable_for_session_user(session)):
			#
				Link.set_store("servicemenu",
				               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
				               L10n.get("pas_http_discuss_post_new"),
				               { "m": "discuss", "s": "post", "a": "new", "dsd": { "dtid": tid } },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#

			subscription_handler = post_parent.get_subscription_handler()

			if (subscription_handler != None and subscription_handler.is_subscribable_for_session_user(session)):
			#
				if (subscription_handler.is_subscribed_by_session_user(session)):
				#
					Link.set_store("servicemenu",
					               Link.TYPE_RELATIVE,
					               L10n.get("pas_http_discuss_topic_unsubscribe"),
					               { "m": "discuss", "s": "topic_subscription", "a": "unsubscribe", "dsd": { "dtid": tid } },
					               icon = "mini-default-option",
					               priority = 3
					              )
				#
				else:
				#
					Link.set_store("servicemenu",
					               Link.TYPE_RELATIVE,
					               L10n.get("pas_http_discuss_topic_subscribe"),
					               { "m": "discuss", "s": "topic_subscription", "a": "subscribe", "dsd": { "dtid": tid } },
					               icon = "mini-default-option",
					               priority = 3
					              )
				#
			#
		#

		topic_parent = (post_parent.load_parent() if (isinstance(post_parent, DataLinker)) else None)
		is_list = isinstance(topic_parent, List)

		if (isinstance(topic_parent, OwnableInstance) and topic_parent.is_writable_for_session_user(session)):
		#
			topic_parent_id = topic_parent.get_id()

			dsd_parameters = ({ "dlid": topic_parent_id }
			                  if (is_list) else
			                  { "doid": tid }
			                 )

			Link.set_store("servicemenu",
			               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			               L10n.get("pas_http_discuss_topic_new"),
			               { "m": "discuss", "s": "topic", "a": "new", "dsd": dsd_parameters },
			               icon = "mini-default-option",
			               priority = 3
			              )

			if (is_list and topic_parent.is_manageable_for_session_user(session)):
			#
				Link.set_store("servicemenu",
				               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
				               L10n.get("pas_http_discuss_list_manage"),
				               { "m": "discuss", "s": "list", "a": "manage", "dsd": { "dlid": topic_parent_id } },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#
		#

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

		if (post_data['time_published'] != post_data['time_sortable']): content['time_updated'] = post_data['time_sortable']

		if (is_topic):
		#
			topic_data = post_parent.get_data_attributes("id",
			                                             "id_main",
			                                             "title",
			                                             "time_sortable",
			                                             "sub_entries",
			                                             "sub_entries_type",
			                                             "author_id",
			                                             "author_ip",
			                                             "posts",
			                                             "description",
			                                             "time_published"
			                                            )
		#
		else:
		#
			topic_data = post_parent.get_data_attributes("id",
			                                             "id_main",
			                                             "title",
			                                             "time_sortable",
			                                             "sub_entries",
			                                             "sub_entries_type"
			                                            )

			topic_data['author_id'] = None
			topic_data['author_ip'] = None
			topic_data['posts'] = None
			topic_data['description'] = None
			topic_data['time_published'] = None
		#

		topic_content = { "id": topic_data['id'],
		                  "title": topic_data['title'],
		                  "author": { "id": topic_data['author_id'], "ip": topic_data['author_ip'] },
		                  "description": topic_data['description'],
		                  "time_published": topic_data['time_published']
		                }

		if (topic_data['time_published'] != topic_data['time_sortable']): topic_content['last_timestamp'] = topic_data['time_sortable']

		if (topic_data['posts'] > 0): topic_content['posts'] = topic_data['posts']
		if (topic_data['sub_entries'] > 0): topic_content['sub_entries'] = { "type": topic_data['sub_entries_type'], "id": topic_data['id'] }

		if (topic_parent != None
		    and ((not isinstance(topic_parent, OwnableInstance))
		         or topic_parent.is_readable_for_session_user(session)
		        )
		   ):
		#
			topic_parent_data = topic_parent.get_data_attributes("id", "id_main", "title")
			topic_content['parent'] = { "id": topic_parent_data['id'], "main_id": topic_parent_data['id_main'], "title": topic_parent_data['title'] }
		#

		content['topic'] = topic_content

		self.response.init(True)
		self.response.set_title(topic_data['title'])
		self.response.set_expires_relative(+30)
		self.response.set_last_modified(post_data['time_sortable'])
		self.response.add_oset_content("discuss.post", content)

		if (self.response.is_supported("html_canonical_url")):
		#
			parameters = { "__virtual__": "/discuss/view/post",
			               "dsd": { "dpid": pid }
			             }

			self.response.set_html_canonical_url(Link().build_url(Link.TYPE_VIRTUAL_PATH, parameters))
		#

		if (self.response.is_supported("html_page_description")
		    and topic_data['description'] != ""
		   ): self.response.set_html_page_description(topic_data['description'])
	#

	def execute_topic(self):
	#
		"""
Action for "topic"

:since: v0.1.00
		"""

		tid = InputFilter.filter_file_path(self.request.get_dsd("dtid", ""))
		page = InputFilter.filter_int(self.request.get_dsd("dpage", 1))

		L10n.init("pas_http_datalinker")
		L10n.init("pas_http_discuss")

		try: topic = Topic.load_id(tid)
		except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_discuss_tid_invalid", 404, _exception = handled_exception)

		session = self.request.get_session()
		if (session != None): topic.set_permission_session(session)

		if (not topic.is_readable()):
		#
			if (session == None or session.get_user_profile() == None): raise TranslatableError("pas_http_discuss_tid_invalid", 404)
			else: raise TranslatableError("core_access_denied", 403)
		#

		if (self.response.is_supported("html_css_files")): self.response.add_theme_css_file("mini_default_sprite.min.css")

		if (topic.is_writable()):
		#
			Link.set_store("servicemenu",
			               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			               L10n.get("pas_http_discuss_post_new"),
			               { "m": "discuss", "s": "post", "a": "new", "dsd": { "dtid": tid } },
			               icon = "mini-default-option",
			               priority = 3
			              )
		#

		subscription_handler = topic.get_subscription_handler()

		if (subscription_handler != None and subscription_handler.is_subscribable_for_session_user(session)):
		#
			if (subscription_handler.is_subscribed_by_session_user(session)):
			#
				Link.set_store("servicemenu",
				               Link.TYPE_RELATIVE,
				               L10n.get("pas_http_discuss_topic_unsubscribe"),
				               { "m": "discuss", "s": "topic_subscription", "a": "unsubscribe", "dsd": { "dtid": tid } },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#
			else:
			#
				Link.set_store("servicemenu",
				               Link.TYPE_RELATIVE,
				               L10n.get("pas_http_discuss_topic_subscribe"),
				               { "m": "discuss", "s": "topic_subscription", "a": "subscribe", "dsd": { "dtid": tid } },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#
		#

		topic_parent = topic.load_parent()
		is_list = isinstance(topic_parent, List)

		if (isinstance(topic_parent, OwnableInstance) and topic_parent.is_writable_for_session_user(session)):
		#
			topic_parent_id = topic_parent.get_id()

			dsd_parameters = ({ "dlid": topic_parent_id }
			                  if (is_list) else
			                  { "doid": tid }
			                 )

			Link.set_store("servicemenu",
			               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
			               L10n.get("pas_http_discuss_topic_new"),
			               { "m": "discuss", "s": "topic", "a": "new", "dsd": dsd_parameters },
			               icon = "mini-default-option",
			               priority = 3
			              )

			if (is_list and topic_parent.is_manageable_for_session_user(session)):
			#
				Link.set_store("servicemenu",
				               (Link.TYPE_RELATIVE | Link.TYPE_JS_REQUIRED),
				               L10n.get("pas_http_discuss_list_manage"),
				               { "m": "discuss", "s": "list", "a": "manage", "dsd": { "dlid": topic_parent_id } },
				               icon = "mini-default-option",
				               priority = 3
				              )
			#
		#

		topic_data = topic.get_data_attributes("id",
		                                       "id_main",
		                                       "title",
		                                       "time_sortable",
		                                       "sub_entries",
		                                       "sub_entries_type",
		                                       "author_id",
		                                       "author_ip",
		                                       "posts",
		                                       "description",
		                                       "time_published"
		                                      )

		content = { "id": topic_data['id'],
		            "title": topic_data['title'],
		            "author": { "id": topic_data['author_id'], "ip": topic_data['author_ip'] },
		            "posts": topic_data['posts'],
		            "description": topic_data['description'],
		            "time_published": topic_data['time_published'],
		            "post_entries": { "id": topic_data['id'], "main_id": topic_data['id_main'], "page": page }
		          }

		if (topic_data['time_published'] != topic_data['time_sortable']): content['last_timestamp'] = topic_data['time_sortable']

		if (topic_data['sub_entries'] > 0): content['sub_entries'] = { "type": topic_data['sub_entries_type'], "id": topic_data['id'] }

		if (topic_parent != None
		    and ((not isinstance(topic_parent, OwnableInstance))
		         or topic_parent.is_readable_for_session_user(session)
		        )
		   ):
		#
			topic_parent_data = topic_parent.get_data_attributes("id", "id_main", "title")
			content['parent'] = { "id": topic_parent_data['id'], "main_id": topic_parent_data['id_main'], "title": topic_parent_data['title'] }
		#

		self.response.init(True)
		self.response.set_title(topic_data['title'])
		self.response.set_expires_relative(+15)
		self.response.set_last_modified(topic_data['time_sortable'])
		self.response.add_oset_content("discuss.topic", content)

		if (self.response.is_supported("html_canonical_url")):
		#
			parameters = { "__virtual__": "/discuss/view/topic",
			               "dsd": { "dtid": tid, "dpage": page }
			             }

			self.response.set_html_canonical_url(Link().build_url(Link.TYPE_VIRTUAL_PATH, parameters))
		#

		if (self.response.is_supported("html_page_description")
		    and topic_data['description'] != ""
		   ): self.response.set_html_page_description(topic_data['description'])
	#
#

##j## EOF