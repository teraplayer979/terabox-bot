def extract_download_data(data):
    """
    Correctly parses the xAPIverse Terabox API response structure.
    Extracts name, size, and download link while handling nested dictionaries safely.
    """
    try:
        # xAPIverse usually wraps the response in a 'data' object or returns it directly
        # The common structure for this specific API is nested within 'data'
        info = data.get("data", {}) if isinstance(data.get("data"), dict) else data
        
        # Extract File Name
        file_name = info.get("file_name") or info.get("filename") or "Unknown File"
        
        # Extract Size
        size = info.get("size") or info.get("filesize") or "Unknown Size"
        
        # Extract Direct Link - checking common nested keys used by xAPIverse
        # Prioritizes direct_link, then falls back to download_link or url
        dl_link = info.get("direct_link") or info.get("download_link") or info.get("url")
        
        # If the link is still not found, check if there's a nested 'download' or 'file' object
        if not dl_link:
            nested_dl = info.get("download", {})
            if isinstance(nested_dl, dict):
                dl_link = nested_dl.get("url") or nested_dl.get("link")

        if not dl_link:
            return "❌ Download link could not be generated for this file."

        # Construct short, safe message to avoid MESSAGE_TOO_LONG
        message = (
            f"📦 **File:** {file_name}\n"
            f"⚖️ **Size:** {size}\n\n"
            f"🚀 **Direct Download Link:**\n`{dl_link}`"
        )
        return message

    except Exception as e:
        logger.error(f"Parsing error: {e}")
        return "⚠️ Error: The API response format has changed. Please contact the administrator."

@bot.message_handler(func=lambda message: True)
def handle_terabox_link(message):
    url = message.text.strip()
    
    # Validation for Terabox domains
    if not any(domain in url for domain in ["terabox", "1024tera", "nephobox", "4shared"]):
        bot.reply_to(message, "❌ Please send a valid Terabox link.")
        return

    status_msg = bot.reply_to(message, "⏳ Generating direct link...")

    try:
        api_url = "https://xapiverse.com/api/terabox"
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": url}

        response = requests.post(api_url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            json_data = response.json()
            
            # Check if API returned an internal error message
            if json_data.get("status") == "error":
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    text=f"❌ **API Error:** {json_data.get('message', 'Unknown Error')}"
                )
                return

            clean_message = extract_download_data(json_data)
            
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=clean_message,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"❌ **Server Error:** API returned status {response.status_code}"
            )

    except Exception as e:
        logger.error(f"Handler Error: {e}")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="⚠️ An unexpected error occurred. Please try again later."
        )
