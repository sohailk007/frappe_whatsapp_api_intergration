# Copyright (c) 2025, Sohail and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe import _
from frappe.utils import now_datetime

class WhatsAppScheduledMessage(Document):
    def validate(self):
        if not self.chat_id:
            frappe.throw(_("Chat ID is required"))
        if not (self.chat_id.endswith('@c.us') or self.chat_id.endswith('@g.us') or self.chat_id.endswith('@newsletter')):
            frappe.throw(_("Invalid chat ID format. Must end with @c.us, @g.us, or @newsletter"))
        if not self.message and not self.media_file:
            frappe.throw(_("Either a text message or a media file is required"))
        if self.schedule_time and self.schedule_time < now_datetime():
            frappe.throw(_("Schedule time must be in the future"))