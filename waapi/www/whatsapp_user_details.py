import frappe

from waapi.api.waapi import get_whatsapp_user_details

def get_context(context):
    """Get context for user details page"""
    context.no_cache = 1
    instance_id = "76432"
    
    # First try to get user data from localStorage (set during QR code scan)
    user_data = frappe.local.form_dict.get("user_data")
    
    if not user_data:
        # If not in request params, fetch fresh from API
        result = get_whatsapp_user_details(instance_id)
        
        if result.get("success"):
            context.user_data = result["user_data"]
        else:
            context.error = result.get("message", "Failed to load user data")
    else:
        try:
            context.user_data = frappe.parse_json(user_data)
        except:
            context.error = "Invalid user data format"