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

from time import time
import re

from dNG.controller.predefined_http_request import PredefinedHttpRequest
from dNG.data.data_linker import DataLinker
from dNG.data.discuss.list import List
from dNG.data.discuss.post import Post as _Post
from dNG.data.discuss.topic import Topic
from dNG.data.http.translatable_error import TranslatableError
from dNG.data.http.translatable_exception import TranslatableException
from dNG.data.ownable_mixin import OwnableMixin as OwnableInstance
from dNG.data.settings import Settings
from dNG.data.tasks.database_proxy import DatabaseProxy as DatabaseTasks
from dNG.data.text.input_filter import InputFilter
from dNG.data.text.l10n import L10n
from dNG.data.xhtml.form.form_tags_textarea_field import FormTagsTextareaField
from dNG.data.xhtml.form.processor import Processor as FormProcessor
from dNG.data.xhtml.form.text_field import TextField
from dNG.data.xhtml.form_tags import FormTags
from dNG.data.xhtml.link import Link
from dNG.data.xhtml.notification_store import NotificationStore
from dNG.database.nothing_matched_exception import NothingMatchedException
from dNG.database.transaction_context import TransactionContext

from .module import Module

class Post(Module):
#
	"""
Service for "m=discuss;s=post"

:author:     direct Netware Group et al.
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    https://www.direct-netware.de/redirect?licenses;gpl
             GNU General Public License 2
	"""

	def execute_edit(self, is_save_mode = False):
	#
		"""
Action for "edit"

:since: v0.1.00
		"""

		pid = InputFilter.filter_file_path(self.request.get_dsd("dpid", ""))

		source_iline = InputFilter.filter_control_chars(self.request.get_dsd("source", "")).strip()
		target_iline = InputFilter.filter_control_chars(self.request.get_dsd("target", "")).strip()

		source = source_iline
		if (source_iline == ""): source_iline = "m=discuss;dsd=dpid+{0}".format(Link.encode_query_value(pid))

		target = target_iline
		if (target_iline == ""): target_iline = source_iline

		L10n.init("pas_http_discuss")

		try: post = _Post.load_id(pid)
		except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_discuss_pid_invalid", 404, _exception = handled_exception)

		session = (self.request.get_session() if (self.request.is_supported("session")) else None)
		if (session is not None): post.set_permission_session(session)

		if (not post.is_writable()): raise TranslatableError("core_access_denied", 403)

		post_parent = post.load_parent()
		if (isinstance(post_parent, OwnableInstance) and (not post_parent.is_writable_for_session_user(session))): raise TranslatableError("core_access_denied", 403)

		topic = (post_parent
		         if (isinstance(post_parent, Topic)) else
		         None
		        )

		topic_parent = None

		if (topic is not None):
		#
			topic_parent = topic.load_parent()
			if (isinstance(topic_parent, OwnableInstance) and (not topic_parent.is_readable_for_session_user(session))): raise TranslatableError("core_access_denied", 403)
		#

		if (self.response.is_supported("html_css_files")): self.response.add_theme_css_file("mini_default_sprite.min.css")

		Link.set_store("servicemenu",
		               Link.TYPE_RELATIVE_URL,
		               L10n.get("core_back"),
		               { "__query__": re.sub("\\_\\_\\w+\\_\\_", "", source_iline) },
		               icon = "mini-default-back",
		               priority = 7
		              )

		if (not DatabaseTasks.is_available()): raise TranslatableException("pas_core_tasks_daemon_not_available")

		post_data = post.get_data_attributes("title", "content")

		form_id = InputFilter.filter_control_chars(self.request.get_parameter("form_id"))

		form = FormProcessor(form_id)

		if (is_save_mode): form.set_input_available()

		field = TextField("dtitle")
		field.set_title(L10n.get("pas_http_discuss_post_title"))
		field.set_value(post_data['title'])
		field.set_required()
		field.set_size(TextField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_topic_title_min", 10)))
		form.add(field)

		field = FormTagsTextareaField("dpost")
		field.set_title(L10n.get("pas_http_discuss_post_content"))
		field.set_value(post_data['content'])
		field.set_required()
		field.set_size(FormTagsTextareaField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_post_content_min", 6)))
		form.add(field)

		if (is_save_mode and form.check()):
		#
			post_title = InputFilter.filter_control_chars(form.get_value("dtitle"))
			post_content = InputFilter.filter_control_chars(form.get_value("dpost"))

			post.set_data_attributes(time_sortable = time(),
			                         title = post_title,
			                         content = FormTags.encode(post_content)
			                        )

			post.save()

			oid = post_parent.get_id()
			lid = (None if (topic_parent is None) else topic_parent.get_id())

			DatabaseTasks.get_instance().add("dNG.pas.discuss.Post.onUpdated.{0}".format(pid), "dNG.pas.discuss.Post.onUpdated", 1, list_id = lid, topic_id = oid, post_id = pid)

			target_iline = target_iline.replace("__id_d__", "{0}".format(pid))
			target_iline = re.sub("\\_\\_\\w+\\_\\_", "", target_iline)

			NotificationStore.get_instance().add_completed_info(L10n.get("pas_http_discuss_done_post_edit"))

			Link.clear_store("servicemenu")

			redirect_request = PredefinedHttpRequest()
			redirect_request.set_iline(target_iline)
			self.request.redirect(redirect_request)
		#
		else:
		#
			content = { "title": L10n.get("pas_http_discuss_post_edit") }

			content['form'] = { "object": form,
			                    "url_parameters": { "__request__": True,
			                                        "a": "edit-save",
			                                        "dsd": { "source": source, "target": target }
			                                      },
			                    "button_title": "pas_http_core_edit"
			                  }

			self.response.init()
			self.response.set_title(content['title'])
			self.response.add_oset_content("core.form", content)
		#
	#

	def execute_edit_save(self):
	#
		"""
Action for "edit-save"

:since: v0.1.00
		"""

		self.execute_edit(self.request.get_type() == "POST")
	#

	def execute_new(self, is_save_mode = False):
	#
		"""
Action for "new"

:since: v0.1.00
		"""

		# pylint: disable=star-args

		tid = InputFilter.filter_file_path(self.request.get_dsd("dtid", ""))
		oid = InputFilter.filter_file_path(self.request.get_dsd("doid", ""))

		source_iline = InputFilter.filter_control_chars(self.request.get_dsd("source", "")).strip()
		target_iline = InputFilter.filter_control_chars(self.request.get_dsd("target", "")).strip()

		if (source_iline == ""):
		#
			source_iline = ("m=discuss;dsd=dpid+{0}".format(Link.encode_query_value(oid))
			                if (tid == "") else
			                "m=discuss;dsd=dtid+{0}".format(Link.encode_query_value(tid))
			               )
		#

		if (target_iline == ""): target_iline = "m=discuss;dsd=dpid+__id_d__"

		if (tid != ""): oid = tid

		self._execute_new("new",
		                  oid,
		                  source_iline = source_iline,
		                  target_iline = target_iline,
		                  is_save_mode = is_save_mode
		                 )
	#

	def _execute_new(self, action, oid = None, pid = None, source_iline = "", target_iline = "", is_save_mode = False):
	#
		"""
Executes the "new" or "reply" action to create a new post.

:param action: Action name
:param oid: Object topic ID
:param pid: Post ID
:param source_iline: Source iline
:param target_iline: Target iline
:param is_save_mode: Is save action

:since: v0.1.00
		"""

		L10n.init("pas_http_core_form")
		L10n.init("pas_http_datalinker")
		L10n.init("pas_http_discuss")

		parent_post = None
		session = (self.request.get_session() if (self.request.is_supported("session")) else None)

		if (pid is not None):
		#
			try: parent_post = _Post.load_id(pid)
			except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_discuss_pid_invalid", 404, _exception = handled_exception)

			if (session is not None): parent_post.set_permission_session(session)

			if (not parent_post.is_writable()): raise TranslatableError("core_access_denied", 403)

			parent_post_parent = parent_post.load_parent()
			if (parent_post_parent is None): raise TranslatableError("pas_http_discuss_pid_invalid", 404, _exception = handled_exception)

			if (isinstance(parent_post_parent, OwnableInstance) and (not parent_post_parent.is_writable_for_session_user(session))): raise TranslatableError("core_access_denied", 403)

			topic = (parent_post_parent
			         if (isinstance(parent_post_parent, Topic)) else
			         None
			        )

			topic_parent = None

			if (topic is not None):
			#
				topic_parent = topic.load_parent()
				if (isinstance(topic_parent, OwnableInstance) and (not topic_parent.is_readable_for_session_user(session))): raise TranslatableError("core_access_denied", 403)
			#
		#
		else:
		#
			try: topic = Topic.load_id(oid)
			except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_datalinker_oid_invalid", 404, _exception = handled_exception)

			if (isinstance(topic, OwnableInstance) and (not OwnableInstance.is_writable_for_session_user(topic, session))): raise TranslatableError("core_access_denied", 403)

			topic_parent = topic.load_parent()
			if (isinstance(topic_parent, OwnableInstance) and (not topic_parent.is_readable_for_session_user(session))): raise TranslatableError("core_access_denied", 403)
		#

		if (self.response.is_supported("html_css_files")): self.response.add_theme_css_file("mini_default_sprite.min.css")

		Link.set_store("servicemenu",
		               Link.TYPE_RELATIVE_URL,
		               L10n.get("core_back"),
		               { "__query__": re.sub("\\_\\_\\w+\\_\\_", "", source_iline) },
		               icon = "mini-default-back",
		               priority = 7
		              )

		if (not DatabaseTasks.is_available()): raise TranslatableException("pas_core_tasks_daemon_not_available")

		form_id = InputFilter.filter_control_chars(self.request.get_parameter("form_id"))

		form = FormProcessor(form_id)
		form.set_context({ "topic": topic })

		post_title = None
		post_content = None

		if (isinstance(parent_post, _Post)):
		#
			post_data = parent_post.get_data_attributes("title", "content")

			post_title = (L10n.get("pas_http_core_form_abbreviation_reply_1")
			              + post_data['title']
			              + L10n.get("pas_http_core_form_abbreviation_reply_2")
			             )

			post_content = "[quote]{0}[/quote]".format(post_data['content'])
		#
		elif (isinstance(topic, Topic)):
		#
			topic_data = topic.get_data_attributes("title")

			post_title = (L10n.get("pas_http_core_form_abbreviation_reply_1")
			              + topic_data['title']
			              + L10n.get("pas_http_core_form_abbreviation_reply_2")
			             )
		#

		if (is_save_mode): form.set_input_available()

		field = TextField("dtitle")
		field.set_title(L10n.get("pas_http_discuss_post_title"))
		field.set_value(post_title)
		field.set_required()
		field.set_size(TextField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_topic_title_min", 10)))
		form.add(field)

		field = FormTagsTextareaField("dpost")
		field.set_title(L10n.get("pas_http_discuss_post_content"))
		field.set_value(post_content)
		field.set_required()
		field.set_size(FormTagsTextareaField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_post_content_min", 6)))
		form.add(field)

		if (is_save_mode and form.check()):
		#
			is_parent_list = isinstance(topic_parent, List)
			is_topic = isinstance(topic, Topic)

			is_datalinker_entry = (True if (is_topic) else isinstance(topic, DataLinker))

			post = _Post()
			pid_d = None

			post_title = InputFilter.filter_control_chars(form.get_value("dtitle"))
			post_content = InputFilter.filter_control_chars(form.get_value("dpost"))

			post_data = { "title": FormTags.encode(post_title),
			              "author_ip": self.request.get_client_host(),
			              "content": FormTags.encode(post_content)
			             }

			user_profile = (None if (session is None) else session.get_user_profile())
			if (user_profile is not None): post_data['author_id'] = user_profile.get_id()

			post_preview = re.sub("(\\n)+", " ", FormTags.sanitize(post_content))
			if (len(post_preview) > 255): post_preview = "{0} ...".format(post_preview[:251])

			with TransactionContext():
			#
				post.set_data_attributes(**post_data)

				if (parent_post is not None): parent_post.add_reply_post(post)
				if (is_parent_list): topic_parent.add_post(post, topic, post_preview)

				if (is_topic): topic.add_post(post, post_preview)
				elif (is_datalinker_entry): topic.add_entry(post)

				post.save()
			#

			pid_d = post.get_id()
			lid = (None if (topic_parent is None) else topic_parent.get_id())

			DatabaseTasks.get_instance().add("dNG.pas.discuss.Post.onAdded.{0}".format(pid_d), "dNG.pas.discuss.Post.onAdded", 1, list_id = lid, topic_id = oid, post_id = pid_d)

			target_iline = target_iline.replace("__id_d__", "{0}".format(pid_d))
			target_iline = re.sub("\\_\\_\\w+\\_\\_", "", target_iline)

			NotificationStore.get_instance().add_completed_info(L10n.get("pas_http_discuss_done_post_{0}".format(action)))

			Link.clear_store("servicemenu")

			redirect_request = PredefinedHttpRequest()
			redirect_request.set_iline(target_iline)
			self.request.redirect(redirect_request)
		#
		else:
		#
			content = { "title": L10n.get("pas_http_discuss_post_{0}".format(action)) }

			content['form'] = { "object": form,
			                    "url_parameters": { "__request__": True,
			                                        "a": "{0}-save".format(action),
			                                        "dsd": { "source": source_iline, "target": target_iline }
			                                      },
			                    "button_title": "pas_core_save"
			                  }

			self.response.init()
			self.response.set_title(content['title'])
			self.response.add_oset_content("core.form", content)
		#
	#

	def execute_new_save(self):
	#
		"""
Action for "new-save"

:since: v0.1.00
		"""

		self.execute_new(self.request.get_type() == "POST")
	#

	def execute_reply(self, is_save_mode = False):
	#
		"""
Action for "reply"

:since: v0.1.00
		"""

		# pylint: disable=star-args

		pid = InputFilter.filter_file_path(self.request.get_dsd("dpid", ""))

		source_iline = InputFilter.filter_control_chars(self.request.get_dsd("source", "")).strip()
		target_iline = InputFilter.filter_control_chars(self.request.get_dsd("target", "")).strip()

		if (source_iline == ""): source_iline = "m=discuss;dsd=dpid+{0}".format(Link.encode_query_value(pid))
		if (target_iline == ""): target_iline = "m=discuss;dsd=dpid+__id_d__"

		self._execute_new("reply",
		                  pid = pid,
		                  source_iline = source_iline,
		                  target_iline = target_iline,
		                  is_save_mode = is_save_mode
		                 )
	#

	def execute_reply_save(self):
	#
		"""
Action for "reply-save"

:since: v0.1.00
		"""

		self.execute_reply(self.request.get_type() == "POST")
	#
#

##j## EOF