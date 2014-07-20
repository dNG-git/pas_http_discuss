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

from time import time
import re

from dNG.pas.controller.predefined_http_request import PredefinedHttpRequest
from dNG.pas.data.data_linker import DataLinker
from dNG.pas.data.ownable_mixin import OwnableMixin as OwnableInstance
from dNG.pas.data.settings import Settings
from dNG.pas.data.discuss.list import List
from dNG.pas.data.discuss.topic import Topic
from dNG.pas.data.discuss.post import Post as _Post
from dNG.pas.data.http.translatable_exception import TranslatableException
from dNG.pas.data.http.translatable_error import TranslatableError
from dNG.pas.data.tasks.database_proxy import DatabaseProxy as DatabaseTasks
from dNG.pas.data.text.input_filter import InputFilter
from dNG.pas.data.text.l10n import L10n
from dNG.pas.data.xhtml.form_tags import FormTags
from dNG.pas.data.xhtml.link import Link
from dNG.pas.data.xhtml.notification_store import NotificationStore
from dNG.pas.data.xhtml.form.form_tags_textarea_field import FormTagsTextareaField
from dNG.pas.data.xhtml.form.processor import Processor as FormProcessor
from dNG.pas.data.xhtml.form.text_field import TextField
from dNG.pas.database.nothing_matched_exception import NothingMatchedException
from dNG.pas.database.transaction_context import TransactionContext
from .module import Module

class Post(Module):
#
	"""
Service for "m=discuss;s=post"

:author:     direct Netware Group
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    http://www.direct-netware.de/redirect.py?licenses;gpl
             GNU General Public License 2
	"""

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

		source = ""

		if (source_iline == ""):
		#
			source_iline = ("m=discuss;dsd=dpid+{0}".format(Link.encode_query_value(oid))
			                if (tid == "") else
			                "m=discuss;dsd=dtid+{0}".format(Link.encode_query_value(tid))
			               )
		#
		else: source = Link.encode_query_value(source_iline)

		target = ""

		if (target_iline == ""): target_iline = "m=discuss;dsd=dpid+__id_d__"
		else: target = Link.encode_query_value(target_iline)

		L10n.init("pas_http_datalinker")
		L10n.init("pas_http_discuss")

		if (tid != ""): oid = tid

		try: topic = Topic.load_id(oid)
		except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_datalinker_oid_invalid", 404, _exception = handled_exception)

		session = self.request.get_session()
		if (isinstance(topic, OwnableInstance) and (not OwnableInstance.is_writable_for_session_user(topic, session))): raise TranslatableError("core_access_denied", 403)

		datalinker_parent = topic.load_parent()
		if (isinstance(datalinker_parent, OwnableInstance) and (not datalinker_parent.is_readable_for_session_user(session))): raise TranslatableError("core_access_denied", 403)

		if (self.response.is_supported("html_css_files")): self.response.add_theme_css_file("mini_default_sprite.min.css")

		Link.set_store("servicemenu",
		               Link.TYPE_RELATIVE,
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

		if (is_save_mode): form.set_input_available()
		elif (isinstance(topic, Topic)):
		#
			topic_data = topic.get_data_attributes("title")
			post_title = topic_data['title']
		#

		field = TextField("dtitle")
		field.set_title(L10n.get("pas_http_discuss_post_title"))
		field.set_value(post_title)
		field.set_required()
		field.set_size(TextField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_topic_title_min", 10)))
		form.add(field)

		field = FormTagsTextareaField("dpost")
		field.set_title(L10n.get("pas_http_discuss_post_content"))
		field.set_required()
		field.set_size(FormTagsTextareaField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_post_content_min", 6)))
		form.add(field)

		if (is_save_mode and form.check()):
		#
			is_parent_list = isinstance(datalinker_parent, List)
			is_topic = isinstance(topic, Topic)

			is_datalinker_entry = (True if (is_topic) else isinstance(topic, DataLinker))

			post = _Post()
			pid_d = None

			with TransactionContext():
			#
				user_profile = (None if (session == None) else session.get_user_profile())

				post_title = InputFilter.filter_control_chars(form.get_value("dtitle"))
				post_content = InputFilter.filter_control_chars(form.get_value("dpost"))

				post_data = { "time_sortable": time(),
				              "title": FormTags.encode(post_title),
				              "author_ip": self.request.get_client_host(),
				              "content": FormTags.encode(post_content)
				             }

				if (user_profile != None): post_data['author_id'] = user_profile.get_id()

				post.set_data_attributes(**post_data)

				post_preview = re.sub("(\\n)+", " ", FormTags.sanitize(post_content))
				if (len(post_preview) > 255): post_preview = "{0} ...".format(post_preview[:251])

				if (is_parent_list): datalinker_parent.add_post(post, topic, post_preview)

				if (is_topic): topic.add_post(post, post_preview)
				elif (is_datalinker_entry): topic.add_entry(post)

				post.save()
			#

			pid_d = post.get_id()
			lid = (None if (datalinker_parent == None) else datalinker_parent.get_id())

			DatabaseTasks.get_instance().add("dNG.pas.discuss.Post.onAdded.{0}".format(pid_d), "dNG.pas.discuss.Post.onAdded", 1, list_id = lid, topic_id = oid, post_id = pid_d)

			target_iline = target_iline.replace("__id_d__", "{0}".format(pid_d))
			target_iline = re.sub("\\_\\_\\w+\\_\\_", "", target_iline)

			NotificationStore.get_instance().add_completed_info(L10n.get("pas_http_discuss_done_post_new"))

			Link.clear_store("servicemenu")

			redirect_request = PredefinedHttpRequest()
			redirect_request.set_iline(target_iline)
			self.request.redirect(redirect_request)
		#
		else:
		#
			content = { "title": L10n.get("pas_http_discuss_post_new") }

			content['form'] = { "object": form,
			                    "url_parameters": { "__request__": True,
			                                        "a": "new-save",
			                                        "dsd": { "source": source, "target": target }
			                                      },
			                    "button_title": "pas_core_save"
			                  }

			self.response.init()
			self.response.set_title(L10n.get("pas_http_discuss_post_new"))
			self.response.add_oset_content("core.form", content)
		#
	#

	def execute_new_save(self):
	#
		"""
Action for "new-save"

:since: v0.1.00
		"""

		self.execute_new(True)
	#
#

##j## EOF