
import requests
import frappe
from frappe import _
from time import time
from requests.exceptions import RequestException
import os
import base64
from datetime import datetime
from frappe.utils import now_datetime, get_datetime, get_files_path

BASE_URL = "https://waapi.app/api/v1"

def get_token():
    """Get API token from WAAPI Settings"""
    settings = frappe.get_single("WAAPI Settings")
    if not settings.api_token:
        frappe.throw(_("WAAPI API Token is not configured in WAAPI Settings"))
    return settings.api_token
    
def get_headers():
    """Get headers for API requests"""
    return {
        "Authorization": f"Bearer {get_token()}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }

@frappe.whitelist(allow_guest=True)
def get_qr_code(instance_id="76432"):
    """Fetch QR code for WhatsApp authentication"""
    try:
        qr_url = f"{BASE_URL}/instances/{instance_id}/client/qr"
        qr_res = requests.get(qr_url, headers=get_headers(), timeout=10)
        qr_res.raise_for_status()
        qr_data = qr_res.json()

        qr_code_value = qr_data.get("qrCode", {}).get("data", {}).get("qr_code")
        
        if qr_code_value and not qr_code_value.startswith("data:image/"):
            qr_code_value = f"data:image/png;base64,{qr_code_value}"
        
        if not qr_code_value:
            frappe.logger().error("No QR code data found in API response")
            return {
                "success": False,
                "message": "No QR code data received from API",
                "error": True
            }

        return {
            "success": True,
            "qr_code": qr_code_value,
            "status": qr_data.get("qrCode", {}).get("status", "waiting"),
            "timestamp": int(time())
        }

    except RequestException as e:
        frappe.log_error(f"WAAPI Connection Error: {str(e)}", "WAAPI Connection Error")
        return {
            "success": False,
            "message": "Could not connect to WAAPI service",
            "error": True,
            "detail": str(e)
        }
    except Exception as e:
        frappe.log_error(f"WAAPI QR Processing Error: {str(e)}", "WAAPI QR Processing Error")
        return {
            "success": False,
            "message": "Error processing the QR code",
            "error": True,
            "detail": str(e)
        }

@frappe.whitelist()
def check_connection_status(instance_id="76432"):
    """Check WhatsApp connection status"""
    try:
        url = f"{BASE_URL}/instances/{instance_id}/client/me"
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            return {
                "connected": True,
                "user_data": {
                    "display_name": data["me"]["data"]["displayName"],
                    "contact_id": data["me"]["data"]["contactId"],
                    "phone_number": data["me"]["data"]["formattedNumber"],
                    "profile_pic": data["me"]["data"]["profilePicUrl"]
                }
            }
        return {"connected": False}

    except RequestException as e:
        frappe.log_error(f"WAAPI Connection Check Error: {str(e)}", "WAAPI Connection Check Error")
        return {
            "success": False,
            "message": "Could not check connection status",
            "error": True,
            "detail": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Connection Status Processing Error: {str(e)}", "Connection Status Processing Error")
        return {
            "success": False,
            "message": "Error checking connection status",
            "error": True,
            "detail": str(e)
        }

@frappe.whitelist()
def get_whatsapp_user_details(instance_id="76432"):
    """Get connected WhatsApp user details"""
    try:
        url = f"{BASE_URL}/instances/{instance_id}/client/me"
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            return {
                "success": False,
                "message": "WhatsApp is not connected",
                "connected": False
            }
            
        return {
            "success": True,
            "connected": True,
            "user_data": {
                "display_name": data["me"]["data"]["displayName"],
                "contact_id": data["me"]["data"]["contactId"],
                "phone_number": data["me"]["data"]["formattedNumber"],
                "profile_pic": data["me"]["data"]["profilePicUrl"]
            }
        }

    except RequestException as e:
        frappe.log_error(f"WAAPI User Details Error: {str(e)}", "WAAPI User Details Error")
        return {
            "success": False,
            "message": "Could not fetch user details",
            "error": True,
            "detail": str(e)
        }
    except Exception as e:
        frappe.log_error(f"User Details Processing Error: {str(e)}", "User Details Processing Error")
        return {
            "success": False,
            "message": "Error processing user details",
            "error": True,
            "detail": str(e)
        }

@frappe.whitelist()
def logout_client(instance_id="76432"):
    """Logout WhatsApp client"""
    try:
        url = f"{BASE_URL}/instances/{instance_id}/client/action/logout"
        response = requests.post(url, headers=get_headers())
        response.raise_for_status()
        
        data = response.json()

        if data.get("data", {}).get("status") == "success":
            return {
                "success": True,
                "message": "Successfully logged out from WhatsApp"
            }
        return {
            "success": False,
            "message": "Failed to logout"
        }
    except Exception as e:
        frappe.log_error(f"Logout Error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def send_whatsapp_message(instance_id="76432", chat_id=None, message=None, mentions=None, reply_to_message_id=None, preview_link=True):
    """Send a WhatsApp text message to a specified chat"""
    try:
        frappe.log_error(f"Sending message to {chat_id}: {message}", "WAAPI Send Message Debug")
        if not chat_id or not message:
            frappe.throw(_("Chat ID and message are required"))

        if not (chat_id.endswith('@c.us') or chat_id.endswith('@g.us') or chat_id.endswith('@newsletter')):
            frappe.throw(_("Invalid chat ID format. Must end with @c.us, @g.us, or @newsletter"))

        url = f"{BASE_URL}/instances/{instance_id}/client/action/send-message"
        payload = {
            "chatId": chat_id,
            "message": message,
            "previewLink": preview_link
        }

        if mentions:
            payload["mentions"] = mentions
        if reply_to_message_id:
            payload["replyToMessageId"] = reply_to_message_id

        response = requests.post(url, json=payload, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            frappe.log_error(f"Message sent successfully to {chat_id}", "WAAPI Send Message Success")
            return {
                "success": True,
                "message": "Message sent successfully",
                "data": {
                    "message_id": data["data"]["_data"]["id"]["_serialized"],
                    "body": data["data"]["_data"]["body"],
                    "from": data["data"]["_data"]["from"]["_serialized"],
                    "to": data["data"]["_data"]["to"]["_serialized"],
                    "timestamp": data["data"]["_data"]["t"]
                }
            }
        else:
            frappe.log_error(f"WAAPI Message Sending Failed: {data.get('message', 'Unknown error')}", "WAAPI Message Sending Error")
            return {
                "success": False,
                "message": data.get("message", "Failed to send message"),
                "error": True
            }

    except RequestException as e:
        frappe.log_error(f"WAAPI Message Sending Connection Error: {str(e)}", "WAAPI Message Sending Error")
        return {
            "success": False,
            "message": "Could not connect to WAAPI service",
            "error": True,
            "detail": str(e)
        }
    except Exception as e:
        frappe.log_error(f"WAAPI Message Processing Error: {str(e)}", "WAAPI Message Processing Error")
        return {
            "success": False,
            "message": "Error processing message",
            "error": True,
            "detail": str(e)
        }

SUPPORTED_MEDIA_TYPES = {
    'image': ['jpg', 'jpeg', 'png', 'gif'],
    'video': ['mp4', '3gp', 'mov'],
    'audio': ['mp3', 'wav', 'ogg', 'm4a'],
    'document': ['pdf', 'doc', 'docx', 'txt', 'xlsx']
}

@frappe.whitelist(allow_guest=True)
def send_whatsapp_media(instance_id="76432", chat_id=None, file_path=None, media_url=None, media_base64=None, media_caption=None, media_name=None):
    """Send a WhatsApp media message to a specified chat"""
    try:
        frappe.log_error(f"Sending media to {chat_id}, file_path: {file_path}, media_name: {media_name}", "WAAPI Send Media Debug")
        if not chat_id:
            frappe.throw(_("Chat ID is required"))

        if not (chat_id.endswith('@c.us') or chat_id.endswith('@g.us') or chat_id.endswith('@newsletter')):
            frappe.throw(_("Invalid chat ID format. Must end with @c.us, @g.us, or @newsletter"))

        if not file_path and not media_url and not media_base64:
            frappe.throw(_("Either file path, media URL, or media base64 is required"))

        if file_path:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            valid_extension = False
            for media_type, extensions in SUPPORTED_MEDIA_TYPES.items():
                if file_ext in extensions:
                    valid_extension = True
                    break
            if not valid_extension:
                frappe.throw(_(f"Unsupported file type. Supported types: {', '.join(sum(SUPPORTED_MEDIA_TYPES.values(), []))}"))

        url = f"{BASE_URL}/instances/{instance_id}/client/action/send-media"
        payload = {
            "chatId": chat_id,
            "mediaCaption": media_caption or "",
            "mediaName": media_name or (os.path.basename(file_path) if file_path else "media_file")
        }

        if file_path:
            abs_path = os.path.join(get_files_path(is_private=1), file_path.lstrip("/private/files/"))
            frappe.log_error(f"Reading file from: {abs_path}", "WAAPI File Path Debug")
            if not os.path.exists(abs_path):
                frappe.throw(_(f"File not found at path: {abs_path}"))
            try:
                with open(abs_path, "rb") as file:
                    media_data = base64.b64encode(file.read()).decode('utf-8')
                payload["mediaBase64"] = media_data
            except Exception as e:
                frappe.throw(_(f"Error reading file: {str(e)}"))
        elif media_url:
            payload["mediaUrl"] = media_url
        elif media_base64:
            payload["mediaBase64"] = media_base64

        response = requests.post(url, json=payload, headers=get_headers(), timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            frappe.log_error(f"Media sent successfully to {chat_id}", "WAAPI Send Media Success")
            return {
                "success": True,
                "message": "Media sent successfully",
                "data": {
                    "message_id": data["data"]["id"]["_serialized"],
                    "body": data["data"]["body"],
                    "from": data["data"]["from"],
                    "to": data["data"]["to"],
                    "timestamp": data["data"]["timestamp"],
                    "media_type": data["data"]["type"],
                    "media_key": data["data"]["mediaKey"]
                }
            }
        else:
            frappe.log_error(f"WAAPI Media Sending Failed: {data.get('message', 'Unknown error')}", "WAAPI Media Sending Error")
            return {
                "success": False,
                "message": data.get("message", "Failed to send media"),
                "error": True
            }

    except RequestException as e:
        frappe.log_error(f"WAAPI Media Sending Connection Error: {str(e)}", "WAAPI Media Sending Error")
        return {
            "success": False,
            "message": "Could not connect to WAAPI service",
            "error": True,
            "detail": str(e)
        }
    except Exception as e:
        frappe.log_error(f"WAAPI Media Processing Error: {str(e)}", "WAAPI Media Processing Error")
        return {
            "success": False,
            "message": "Error processing media",
            "error": True,
            "detail": str(e)
        }

@frappe.whitelist(allow_guest=True)
def schedule_whatsapp_message(
    instance_id="76432",
    chat_id=None,
    message=None,
    media_base64=None,
    media_caption=None,
    media_name=None,
    mentions=None,
    reply_to_message_id=None,
    preview_link=True,
    schedule_time=None
):
    """Schedule a WhatsApp message or media for a specific date and time"""
    try:
        frappe.log_error(f"Scheduling message for {chat_id} at {schedule_time}", "WAAPI Schedule Debug")
        if not chat_id:
            frappe.throw(_("Chat ID is required"))
        if not (chat_id.endswith('@c.us') or chat_id.endswith('@g.us') or chat_id.endswith('@newsletter')):
            frappe.throw(_("Invalid chat ID format. Must end with @c.us, @g.us, or @newsletter"))
        if not message and not media_base64:
            frappe.throw(_("Either a text message or a media file is required"))
        if not schedule_time:
            frappe.throw(_("Schedule time is required"))
        
        schedule_time_dt = get_datetime(schedule_time)
        if schedule_time_dt < now_datetime():
            frappe.throw(_("Schedule time must be in the future"))

        if media_base64 and media_name:
            file_ext = os.path.splitext(media_name)[1].lower().lstrip('.')
            valid_extension = False
            for media_type, extensions in SUPPORTED_MEDIA_TYPES.items():
                if file_ext in extensions:
                    valid_extension = True
                    break
            if not valid_extension:
                frappe.throw(_(f"Unsupported file type. Supported types: {', '.join(sum(SUPPORTED_MEDIA_TYPES.values(), []))}"))

        scheduled_message = frappe.get_doc({
            "doctype": "WhatsApp Scheduled Message",
            "instance_id": instance_id,
            "chat_id": chat_id,
            "message": message,
            "media_file": None,
            "media_caption": media_caption,
            "media_name": media_name,
            "mentions": mentions,
            "reply_to_message_id": reply_to_message_id,
            "preview_link": preview_link,
            "schedule_time": schedule_time_dt,
            "status": "Pending"
        })
        print(scheduled_message)
        print(schedule_time)

        if media_base64:
            file_name = media_name or f"scheduled_media_{frappe.generate_hash(length=8)}"
            try:
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": file_name,
                    "content": base64.b64decode(media_base64),
                    "is_private": 1
                })
                file_doc.insert()
                scheduled_message.media_file = file_doc.file_url
                frappe.log_error(f"Media file saved: {file_doc.file_url}", "WAAPI File Save Debug")
            except Exception as e:
                frappe.log_error(f"Error saving media file: {str(e)}", "WAAPI File Save Error")
                frappe.throw(_(f"Error saving media file: {str(e)}"))

        scheduled_message.insert()
        frappe.log_error(f"Scheduled message created: {scheduled_message.name}", "WAAPI Schedule Success")

        return {
            "success": True,
            "message": f"Message scheduled for {schedule_time_dt}",
            "docname": scheduled_message.name
        }

    except Exception as e:
        frappe.log_error(f"WAAPI Scheduling Error: {str(e)}", "WAAPI Scheduling Error")
        return {
            "success": False,
            "message": "Error scheduling message",
            "error": True,
            "detail": str(e)
        }

@frappe.whitelist(allow_guest=True)
def process_scheduled_messages():
    """Scheduled job to process pending WhatsApp messages"""
    try:
        frappe.log_error("Starting process_scheduled_messages", "WAAPI Scheduler Debug")
        pending_messages = frappe.get_all(
            "WhatsApp Scheduled Message",
            filters={
                "status": "Pending",
                "schedule_time": ["<=", now_datetime()]
            },
            fields=["name", "instance_id", "chat_id", "message", "media_file", "media_caption", "media_name", "mentions", "reply_to_message_id", "preview_link"]
        )
        frappe.log_error(f"Found {len(pending_messages)} pending messages", "WAAPI Scheduler Debug")

        for msg in pending_messages:
            frappe.log_error(f"Processing message {msg.name} for {msg.chat_id}", "WAAPI Scheduler Debug")
            frappe.db.set_value("WhatsApp Scheduled Message", msg.name, "status", "Processing")
            frappe.db.commit()  # Ensure status update is committed
            try:
                if msg.message:
                    response = send_whatsapp_message(
                        instance_id=msg.instance_id,
                        chat_id=msg.chat_id,
                        message=msg.message,
                        mentions=msg.mentions,
                        reply_to_message_id=msg.reply_to_message_id,
                        preview_link=msg.preview_link
                    )
                    if not response.get("success"):
                        frappe.db.set_value("WhatsApp Scheduled Message", msg.name, {
                            "status": "Failed",
                            "response": response.get("message", "Unknown error")
                        })
                        frappe.db.commit()
                        frappe.log_error(f"Text message failed for {msg.name}: {response.get('message')}", "WAAPI Scheduler Error")
                        continue

                if msg.media_file:
                    abs_path = os.path.join(get_files_path(is_private=1), msg.media_file.lstrip("/private/files/"))
                    frappe.log_error(f"Attempting to read media file: {abs_path}", "WAAPI Scheduler File Debug")
                    if not os.path.exists(abs_path):
                        frappe.db.set_value("WhatsApp Scheduled Message", msg.name, {
                            "status": "Failed",
                            "response": f"Media file not found: {abs_path}"
                        })
                        frappe.db.commit()
                        frappe.log_error(f"Media file not found for {msg.name}: {abs_path}", "WAAPI Scheduler Error")
                        continue
                    response = send_whatsapp_media(
                        instance_id=msg.instance_id,
                        chat_id=msg.chat_id,
                        file_path=abs_path,
                        media_caption=msg.media_caption,
                        media_name=msg.media_name
                    )
                    if not response.get("success"):
                        frappe.db.set_value("WhatsApp Scheduled Message", msg.name, {
                            "status": "Failed",
                            "response": response.get("message", "Unknown error")
                        })
                        frappe.db.commit()
                        frappe.log_error(f"Media message failed for {msg.name}: {response.get('message')}", "WAAPI Scheduler Error")
                        continue

                frappe.db.set_value("WhatsApp Scheduled Message", msg.name, {
                    "status": "Sent",
                    "response": "Message sent successfully"
                })
                frappe.db.commit()
                frappe.log_error(f"Message {msg.name} sent successfully", "WAAPI Scheduler Success")

            except Exception as e:
                frappe.log_error(f"Scheduled Message Processing Error for {msg.name}: {str(e)}", "WAAPI Scheduler Error")
                frappe.db.set_value("WhatsApp Scheduled Message", msg.name, {
                    "status": "Failed",
                    "response": str(e)
                })
                frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Scheduled Messages Processing Error: {str(e)}", "WAAPI Scheduler Error")