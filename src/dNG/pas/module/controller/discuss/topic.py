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

from dNG.pas.controller.predefined_http_request import PredefinedHttpRequest
from dNG.pas.data.ownable_mixin import OwnableMixin as OwnableInstance
from dNG.pas.data.settings import Settings
from dNG.pas.data.discuss.list import List
from dNG.pas.data.discuss.topic import Topic as _Topic
from dNG.pas.data.discuss.post import Post
from dNG.pas.data.http.translatable_error import TranslatableError
from dNG.pas.data.http.translatable_exception import TranslatableException
from dNG.pas.data.tasks.database_proxy import DatabaseProxy as DatabaseTasks
from dNG.pas.data.text.input_filter import InputFilter
from dNG.pas.data.text.l10n import L10n
from dNG.pas.data.xhtml.form_tags import FormTags
from dNG.pas.data.xhtml.link import Link
from dNG.pas.data.xhtml.notification_store import NotificationStore
from dNG.pas.data.xhtml.form.form_tags_textarea_field import FormTagsTextareaField
from dNG.pas.data.xhtml.form.processor import Processor as FormProcessor
from dNG.pas.data.xhtml.form.text_field import TextField
from dNG.pas.data.xhtml.form.textarea_field import TextareaField
from dNG.pas.database.nothing_matched_exception import NothingMatchedException
from dNG.pas.database.transaction_context import TransactionContext
from .module import Module

class Topic(Module):
#
	"""
Service for "m=discuss;s=topic"

:author:     direct Netware Group
:copyright:  (C) direct Netware Group - All rights reserved
:package:    pas.http
:subpackage: discuss
:since:      v0.1.00
:license:    https://www.direct-netware.de/redirect?licenses;gpl
             GNU General Public License 2
	"""

	def _check_tag_unique(self, field, validator_context):
	#
		"""
Form validator that checks if the tag is unique if defined.

:param field: Form field
:param validator_context: Form validator context

:return: (str) Error message; None on success
:since:  v0.1.00
		"""

		_return = None

		value = field.get_value()

		if ((validator_context['form'] == "new" or value != validator_context['current_tag'])
		    and len(value) > 0
		    and (not validator_context['list'].is_tag_unique(value))
		   ): _return = L10n.get("pas_http_datalinker_form_error_tag_not_unique")

		return _return
	#

	def execute_new(self, is_save_mode = False):
	#
		"""
Action for "new"

:since: v0.1.00
		"""

		# pylint: disable=star-args

		lid = InputFilter.filter_file_path(self.request.get_dsd("dlid", ""))
		oid = InputFilter.filter_file_path(self.request.get_dsd("doid", ""))

		source_iline = InputFilter.filter_control_chars(self.request.get_dsd("source", "")).strip()
		target_iline = InputFilter.filter_control_chars(self.request.get_dsd("target", "")).strip()

		source = source_iline

		if (source_iline == ""):
		#
			source_iline = ("m=discuss;dsd=dtid+{0}".format(Link.encode_query_value(oid))
			                if (lid == "") else
			                "m=discuss;dsd=dlid+{0}".format(Link.encode_query_value(lid))
			               )
		#

		target = target_iline
		if (target_iline == ""): target_iline = "m=discuss;dsd=dtid+__id_d__"

		L10n.init("pas_http_datalinker")
		L10n.init("pas_http_discuss")

		if (lid != ""): oid = lid

		try: _list = List.load_id(oid)
		except NothingMatchedException as handled_exception: raise TranslatableError("pas_http_datalinker_oid_invalid", 404, _exception = handled_exception)

		is_manageable = False
		session = self.request.get_session()

		if (isinstance(_list, OwnableInstance)):
		#
			if (not _list.is_writable_for_session_user(session)): raise TranslatableError("core_access_denied", 403)
			is_manageable = _list.is_manageable_for_session_user(session)
		#
		elif (session != None):
		#
			user_profile = session.get_user_profile()
			if (user_profile != None): is_manageable = user_profile.is_type("ad")
		#

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
		form.set_context({ "form": "new", "list": _list })

		if (is_save_mode): form.set_input_available()

		field = TextField("dtitle")
		field.set_title(L10n.get("pas_http_discuss_topic_title"))
		field.set_required()
		field.set_size(TextField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_topic_title_min", 10)))
		form.add(field)

		if (is_manageable):
		#
			field = TextField("dtag")
			field.set_title(L10n.get("pas_http_discuss_topic_tag"))
			field.set_size(TextField.SIZE_SMALL)
			field.set_limits(_max = 255)
			field.set_validators([ self._check_tag_unique ])
			form.add(field)
		#

		field = TextareaField("ddescription")
		field.set_title(L10n.get("pas_http_discuss_topic_description"))
		field.set_size(TextField.SIZE_SMALL)
		field.set_limits(_max = 255)
		form.add(field)

		field = FormTagsTextareaField("dpost")
		field.set_title(L10n.get("pas_http_discuss_post_content"))
		field.set_required()
		field.set_size(FormTagsTextareaField.SIZE_LARGE)
		field.set_limits(int(Settings.get("pas_http_discuss_post_content_min", 6)))
		form.add(field)

		if (is_save_mode and form.check()):
		#
			is_list = isinstance(_list, List)

			is_datalinker_entry = (True if (is_list) else isinstance(_list, List))

			topic = _Topic()
			tid_d = None

			post = Post()

			topic_timestamp = time()
			topic_title = InputFilter.filter_control_chars(form.get_value("dtitle"))
			topic_description = InputFilter.filter_control_chars(form.get_value("ddescription"))

			topic_tag = (InputFilter.filter_control_chars(form.get_value("dtag"))
			             if (is_manageable) else
			             None
			            )

			post_content = InputFilter.filter_control_chars(form.get_value("dpost"))

			post_preview = re.sub("(\\n)+", " ", FormTags.sanitize(post_content))
			if (len(post_preview) > 255): post_preview = "{0} ...".format(post_preview[:251])

			with TransactionContext():
			#
				topic_data = { "time_sortable": topic_timestamp,
				               "title": FormTags.encode(topic_title),
				               "tag": topic_tag,
				               "author_ip": self.request.get_client_host(),
				               "description": topic_description
				             }

				user_profile = (None if (session == None) else session.get_user_profile())

				if (user_profile != None): topic_data['author_id'] = user_profile.get_id()

				topic.set_data_attributes(**topic_data)

				post_data = { "time_sortable": topic_timestamp,
				              "title": FormTags.encode(topic_title),
				              "author_ip": self.request.get_client_host(),
				              "content": FormTags.encode(post_content)
				             }

				if (user_profile != None): post_data['author_id'] = user_profile.get_id()

				post.set_data_attributes(**post_data)

				if (is_list): _list.add_topic(topic, post, post_preview)
				elif (is_datalinker_entry): _list.add_entry(topic)

				topic.add_post(post, post_preview)

				topic.save()
				post.save()
			#

			pid = post.get_id()
			tid_d = topic.get_id()

			DatabaseTasks.get_instance().add("dNG.pas.discuss.Topic.onAdded.{0}".format(tid_d), "dNG.pas.discuss.Topic.onAdded", 1, list_id = oid, topic_id = tid_d, post_id = pid)

			target_iline = target_iline.replace("__id_d__", "{0}".format(tid_d))
			target_iline = re.sub("\\_\\_\\w+\\_\\_", "", target_iline)

			NotificationStore.get_instance().add_completed_info(L10n.get("pas_http_discuss_done_topic_new"))

			Link.clear_store("servicemenu")

			redirect_request = PredefinedHttpRequest()
			redirect_request.set_iline(target_iline)
			self.request.redirect(redirect_request)
		#
		else:
		#
			content = { "title": L10n.get("pas_http_discuss_topic_new") }

			content['form'] = { "object": form,
			                    "url_parameters": { "__request__": True,
			                                        "a": "new-save",
			                                        "dsd": { "source": source, "target": target }
			                                      },
			                    "button_title": "pas_core_save"
			                  }

			self.response.init()
			self.response.set_title(L10n.get("pas_http_discuss_topic_new"))
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
#

##j## EOF