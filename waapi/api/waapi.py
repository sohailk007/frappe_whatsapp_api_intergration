import requests
import frappe
from frappe import _
from time import time
from requests.exceptions import RequestException
import os
import base64

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

# Supported media types
SUPPORTED_MEDIA_TYPES = {
    'image': ['jpg', 'jpeg', 'png', 'gif'],
    'video': ['mp4', '3gp', 'mov'],
    'audio': ['mp3', 'wav', 'ogg', 'm4a'],
    'document': ['pdf', 'doc', 'docx', 'txt', 'xlsx']
}

@frappe.whitelist()
def send_whatsapp_media(instance_id="76432", chat_id=None, file_path=None, media_url=None, media_base64=None, media_caption=None, media_name=None):
    """Send a WhatsApp media message to a specified chat"""
    try:
        if not chat_id:
            frappe.throw(_("Chat ID is required"))

        if not (chat_id.endswith('@c.us') or chat_id.endswith('@g.us') or chat_id.endswith('@newsletter')):
            frappe.throw(_("Invalid chat ID format. Must end with @c.us, @g.us, or @newsletter"))

        if not file_path and not media_url and not media_base64:
            frappe.throw(_("Either file path, media URL, or media base64 is required"))

        # Validate file extension if file_path is provided
        if file_path:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            valid_extension = False
            for media_type, extensions in SUPPORTED_MEDIA_TYPES.items():
                if file_ext in extensions:
                    valid_extension = True
                    break
            if not valid_extension:
                frappe.throw(_(f"Unsupported file type. Supported types: {', '.join(sum(SUPPORTED_MEDIA_TYPES.values(), []))}"))

        # Prepare payload
        url = f"{BASE_URL}/instances/{instance_id}/client/action/send-media"
        payload = {
            "chatId": chat_id,
            "mediaCaption": media_caption or "",
            "mediaName": media_name or (os.path.basename(file_path) if file_path else "media_file")
        }

        # Handle file upload (base64) or media URL
        if file_path:
            try:
                with open(file_path, "rb") as file:
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