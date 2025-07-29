import requests
import frappe
from frappe import _
from time import time
from requests.exceptions import RequestException

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
        # Get QR code from API
        qr_url = f"{BASE_URL}/instances/{instance_id}/client/qr"
        qr_res = requests.get(qr_url, headers=get_headers(), timeout=10)
        qr_res.raise_for_status()
        qr_data = qr_res.json()

        # Extract QR code data
        qr_code_value = qr_data.get("qrCode", {}).get("data", {}).get("qr_code")
        
        # If API returns raw base64 without data URL prefix
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

        #print(f"User details API response: {data}") 
        
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

        #print(f"Logout API response: {data}")

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

@frappe.whitelist()
def send_whatsapp_message(instance_id="76432", chat_id=None, message=None, mentions=None, reply_to_message_id=None, preview_link=True):
    """Send a WhatsApp text message to a specified chat"""
    try:
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
    
@frappe.whitelist()
def send_whatsapp_media(instance_id="76432", chat_id=None, media_url=None, media_base64=None, media_name=None, media_caption=None, reply_to_message_id=None, preview_link=True, as_sticker=False, as_voice=False, as_document=False):
    """Send a WhatsApp media message (image, video, audio, document) to a specified chat"""
    try:
        if not chat_id:
            frappe.throw(_("Chat ID is required"))
        if not (media_url or media_base64):
            frappe.throw(_("Either media URL or Base64 content is required"))
        if media_base64 and not media_name:
            frappe.throw(_("Media name is required when sending Base64 content"))

        if not (chat_id.endswith('@c.us') or chat_id.endswith('@g.us') or chat_id.endswith('@newsletter')):
            frappe.throw(_("Invalid chat ID format. Must end with @c.us, @g.us, or @newsletter"))

        # Validate supported media types for Base64
        if media_base64:
            ext = media_name.split('.')[-1].lower()
            supported_extensions = {
                'image': ['jpg', 'jpeg', 'png', 'gif'],
                'video': ['mp4', '3gp', 'mov'],
                'audio': ['mp3', 'wav', 'ogg', 'm4a'],
                'document': ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls', 'ppt', 'pptx']
            }
            media_type = None
            for type_, exts in supported_extensions.items():
                if ext in exts:
                    media_type = type_
                    break
            if not media_type:
                frappe.throw(_("Unsupported file extension for Base64 media"))

        url = f"{BASE_URL}/instances/{instance_id}/client/action/send-media"
        payload = {
            "chatId": chat_id,
            "previewLink": preview_link,
            "asSticker": as_sticker,
            "asVoice": as_voice,
            "asDocument": as_document
        }

        if media_url:
            payload["mediaUrl"] = media_url
        if media_base64:
            payload["mediaBase64"] = media_base64
        if media_name:
            payload["mediaName"] = media_name
        if media_caption:
            payload["mediaCaption"] = media_caption
        if reply_to_message_id:
            payload["replyToMessageId"] = reply_to_message_id

        response = requests.post(url, json=payload, headers=get_headers(), timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return {
                "success": True,
                "message": "Media message sent successfully",
                "data": {
                    "message_id": data["data"]["_data"]["id"]["_serialized"],
                    "type": data["data"]["_data"]["type"],
                    "from": data["data"]["_data"]["from"],
                    "to": data["data"]["_data"]["to"],
                    "timestamp": data["data"]["_data"]["t"],
                    "has_media": data["data"]["_data"]["hasMedia"],
                    "media_key": data["data"]["_data"].get("mediaKey"),
                    "mimetype": data["data"]["_data"].get("mimetype")
                }
            }
        else:
            frappe.log_error(f"WAAPI Media Sending Failed: {data.get('message', 'Unknown error')}", "WAAPI Media Sending Error")
            return {
                "success": False,
                "message": data.get("message", "Failed to send media message"),
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
            "message": "Error processing media message",
            "error": True,
            "detail": str(e)
        }
    
