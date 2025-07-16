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
    
DEFAULT_INSTANCE_ID = "76432"

@frappe.whitelist()
def send_text_message(chat_id, message, mentions=None, reply_to_message_id=None, preview_link=True, instance_id=DEFAULT_INSTANCE_ID):
    """
    Send text message to WhatsApp chat
    Args:
        chat_id: Format <countrycode>@c.us for individuals or @g.us for groups
        message: Text message content
        mentions: Array of contact IDs to mention (only for group chats)
        reply_to_message_id: Message ID to reply to (format: {fromMe}{chatId}{messageId})
        preview_link: Whether to show link previews (default True)
        instance_id: WhatsApp instance ID
    """
    try:
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
        
        response = requests.post(url, headers=get_headers(), json=payload)
        response.raise_for_status()
        
        data = response.json()

        print(f"Send message API repsonse: {data}")
        
        if data.get("status") == "success":
            # Log the message in Frappe
            log_message(chat_id, message, data, is_media=False)
            return {
                "success": True,
                "message": "Message sent successfully",
                "message_id": data.get("data", {}).get("_data", {}).get("id", {}).get("_serialized")
            }
        else:
            return {
                "success": False,
                "message": "Failed to send message",
                "error": data
            }
            
    except RequestException as e:
        frappe.log_error(f"WAAPI Send Message Error: {str(e)}", "WAAPI Send Message Error")
        return {
            "success": False,
            "message": "Could not connect to WAAPI service",
            "error": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Message Processing Error: {str(e)}", "Message Processing Error")
        return {
            "success": False,
            "message": "Error processing message",
            "error": str(e)
        }

@frappe.whitelist()
def send_media_message(chat_id, media_url=None, media_base64=None, media_name=None, 
                      media_caption=None, reply_to_message_id=None, preview_link=True,
                      as_sticker=False, as_voice=False, as_document=False, 
                      instance_id=DEFAULT_INSTANCE_ID):
    """
    Send media message to WhatsApp chat
    Args:
        chat_id: Format <countrycode>@c.us for individuals or @g.us for groups
        media_url: URL of media file (alternative to base64)
        media_base64: Base64 encoded media content (alternative to URL)
        media_name: Filename required for base64 media
        media_caption: Optional caption for media
        reply_to_message_id: Message ID to reply to
        preview_link: Whether to show link previews
        as_sticker: Send image as sticker
        as_voice: Send audio as voice message
        as_document: Send media as document
        instance_id: WhatsApp instance ID
    """
    try:
        if not media_url and not media_base64:
            frappe.throw(_("Either media_url or media_base64 must be provided"))
            
        if media_base64 and not media_name:
            frappe.throw(_("media_name is required when sending base64 media"))
            
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
        else:
            payload["mediaBase64"] = media_base64
            payload["mediaName"] = media_name
            
        if media_caption:
            payload["mediaCaption"] = media_caption
            
        if reply_to_message_id:
            payload["replyToMessageId"] = reply_to_message_id
        
        response = requests.post(url, headers=get_headers(), json=payload)
        response.raise_for_status()
        
        data = response.json()

        print(f"Send media API response: {data}")
        
        if data.get("status") == "success":
            # Log the media message in Frappe
            log_message(chat_id, media_caption or "Media message", data, is_media=True)
            return {
                "success": True,
                "message": "Media sent successfully",
                "message_id": data.get("data", {}).get("_data", {}).get("id", {}).get("_serialized")
            }
        else:
            return {
                "success": False,
                "message": "Failed to send media",
                "error": data
            }
            
    except RequestException as e:
        frappe.log_error(f"WAAPI Send Media Error: {str(e)}", "WAAPI Send Media Error")
        return {
            "success": False,
            "message": "Could not connect to WAAPI service",
            "error": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Media Processing Error: {str(e)}", "Media Processing Error")
        return {
            "success": False,
            "message": "Error processing media",
            "error": str(e)
        }

def log_message(chat_id, message_content, api_response, is_media=False):
    """Create a WhatsApp Message document in Frappe"""
    try:
        msg_data = api_response.get("data", {}).get("_data", {})
        doc = frappe.get_doc({
            "doctype": "WhatsApp Message",
            "chat_id": chat_id,
            "message_content": message_content,
            "message_id": msg_data.get("id", {}).get("_serialized"),
            "timestamp": msg_data.get("timestamp"),
            "direction": "Outgoing",
            "status": "Sent",
            "is_media": is_media,
            "api_response": frappe.as_json(api_response, indent=2)
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error logging WhatsApp message: {str(e)}")

@frappe.whitelist()
def get_chat_list(offset=0, limit=50, instance_id=DEFAULT_INSTANCE_ID):
    """Get list of WhatsApp chats with pagination"""
    try:
        # First verify connection status
        status = check_connection_status(instance_id)
        if not status.get("connected"):
            return {
                "success": False,
                "message": "WhatsApp is not connected. Please scan QR code first.",
                "connected": False
            }

        url = f"{BASE_URL}/instances/{instance_id}/client/action/get-chats"
        payload = {
            "offset": offset,
            "limit": limit
        }
        
        response = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"Chat list API response: {data}")
        frappe.logger().debug(f"Chat list API response: {data}")

        if data.get("status") == "success":
            chats = []
            for chat in data.get("data", []):
                try:
                    chats.append({
                        "id": chat.get("id", {}).get("_serialized", ""),
                        "name": chat.get("name", "Unknown Chat"),
                        "is_group": chat.get("isGroup", False),
                        "unread_count": chat.get("unreadCount", 0),
                        "timestamp": chat.get("timestamp", 0),
                        "last_message": chat.get("lastMessage", {}).get("body", ""),
                        "last_message_time": chat.get("lastMessage", {}).get("timestamp", 0),
                        "archived": chat.get("archived", False),
                        "pinned": chat.get("pinned", False)
                    })
                except Exception as e:
                    frappe.log_error(f"Error processing chat {chat}: {str(e)}")
                    continue

            return {
                "success": True,
                "chats": chats,
                "total": len(chats),
                "offset": offset,
                "limit": limit,
                "has_more": len(chats) == limit  # Simple pagination indicator
            }
        else:
            return {
                "success": False,
                "message": data.get("message", "Failed to get chat list"),
                "error": data
            }
            
    except RequestException as e:
        frappe.log_error(f"WAAPI Connection Error: {str(e)}", "WAAPI Chat List Error")
        return {
            "success": False,
            "message": "Could not connect to WAAPI service",
            "error": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Chat List Processing Error: {str(e)}", "WAAPI Chat List Error")
        return {
            "success": False,
            "message": "Error processing chat list",
            "error": str(e)
        }

@frappe.whitelist()
def get_chat_history(chat_id, limit=50, instance_id=DEFAULT_INSTANCE_ID):
    """Get chat history for a specific chat"""
    try:
        url = f"{BASE_URL}/instances/{instance_id}/client/action/get-chat-history"
        
        payload = {
            "chatId": chat_id,
            "limit": limit
        }
        
        response = requests.post(url, headers=get_headers(), json=payload)
        response.raise_for_status()
        
        data = response.json()

        print(f"Chat history API response: {data}")
        
        if data.get("status") == "success":
            messages = []
            for msg in data.get("data", {}).get("messages", []):
                try:
                    msg_data = msg.get("_data", msg)
                    messages.append({
                        "id": msg_data.get("id", {}).get("_serialized", ""),
                        "body": msg_data.get("body", ""),
                        "type": msg_data.get("type", "chat"),
                        "timestamp": msg_data.get("timestamp", 0),
                        "from_me": msg_data.get("id", {}).get("fromMe", False),
                        "status": msg_data.get("status", ""),
                        "media_url": msg_data.get("mediaUrl"),
                        "mimetype": msg_data.get("mimetype")
                    })
                except Exception as e:
                    frappe.log_error(f"Error processing message {msg}: {str(e)}")
                    continue

            return {
                "success": True,
                "messages": messages,
                "chat_id": chat_id
            }
        else:
            return {
                "success": False,
                "message": "Failed to get chat history",
                "error": data
            }
            
    except Exception as e:
        frappe.log_error(f"Chat History Error: {str(e)}", "Chat History Error")
        return {
            "success": False,
            "message": "Error getting chat history",
            "error": str(e)
        }

@frappe.whitelist()
def get_chat_info(chat_id, instance_id=DEFAULT_INSTANCE_ID):
    """Get information about a specific chat"""
    try:
        url = f"{BASE_URL}/instances/{instance_id}/client/action/get-chat-info"
        
        payload = {
            "chatId": chat_id
        }
        
        response = requests.post(url, headers=get_headers(), json=payload)
        response.raise_for_status()
        
        data = response.json()

        print(f"Chat Info API response: {data}")
        
        if data.get("status") == "success":
            return {
                "success": True,
                "chat": data.get("data", {})
            }
        else:
            return {
                "success": False,
                "message": "Failed to get chat info",
                "error": data
            }
            
    except Exception as e:
        frappe.log_error(f"Chat Info Error: {str(e)}", "Chat Info Error")
        return {
            "success": False,
            "message": "Error getting chat info",
            "error": str(e)
        }

