import random
import string
import requests
import telebot
from telebot import types

# Your Telegram Bot Token
TOKEN = "8873451365:AAEfqeefjK4puu_Q2Tj8GDPOywsJpXuG_iE"
bot = telebot.TeleBot(TOKEN)

# Store user session data
user_data = {}


@bot.message_handler(commands=['start'])
def send_welcome(msg):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(types.KeyboardButton("🚀 Open Admin Panel"))
  bot.send_message(
      msg.chat.id,
      "Welcome! Click the button below to manage your Firebase Realtime"
      " Database.",
      reply_markup=markup,
  )


@bot.message_handler(func=lambda message: message.text == "🚀 Open Admin Panel")
def ask_database_url(msg):
  sent_msg = bot.send_message(
      msg.chat.id,
      "Please enter your **Firebase Database URL**:\n(Example:"
      " https://your-app-default-rtdb.firebaseio.com)",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(sent_msg, verify_and_show_dashboard)


def verify_and_show_dashboard(msg):
  chat_id = msg.chat.id
  db_url = msg.text.strip().rstrip('/')

  if not db_url.startswith("https://") or not (
      db_url.endswith(".firebaseio.com") or db_url.endswith(".firebasedatabase.app")
  ):
    bot.send_message(
        chat_id,
        "❌ Invalid Database URL! URL must end with `.firebaseio.com` or"
        " `.firebasedatabase.app`.",
    )
    return

  try:
    test_res = requests.get(f"{db_url}/.json?print=silent", timeout=5)
    if test_res.status_code not in [200, 204]:
      bot.send_message(
          chat_id,
          f"❌ Connection Failed! Status Code: `{test_res.status_code}`\nPlease"
          " check your Firebase Rules.",
          parse_mode="Markdown",
      )
      return
  except Exception as e:
    bot.send_message(chat_id, f"❌ Error: {str(e)}")
    return

  user_data[chat_id] = {"db_url": db_url}
  show_main_dashboard(chat_id)


def show_main_dashboard(chat_id):
  db_url = user_data[chat_id]["db_url"]
  db_name = db_url.split("//")[1].split(".")[0]

  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(
      types.InlineKeyboardButton(
          "🔑 Generate Auto Key", callback_data="gen_auto_key"
      ),
      types.InlineKeyboardButton(
          "✍️ Create Custom Key", callback_data="gen_custom_key"
      ),
      types.InlineKeyboardButton("📋 View All Keys", callback_data="view_keys"),
      types.InlineKeyboardButton(
          "🗑️ Delete Specific Key", callback_data="delete_key_prompt"
      ),
      types.InlineKeyboardButton("📤 Push App Update", callback_data="set_update"),
      types.InlineKeyboardButton(
          "🗑️ Delete App Update", callback_data="del_update"
      ),
      types.InlineKeyboardButton(
          "🔒 Maintenance Mode", callback_data="toggle_maintenance"
      ),
      types.InlineKeyboardButton(
          "📢 Broadcast Notice", callback_data="set_notice"
      ),
      types.InlineKeyboardButton("📊 Database Stats", callback_data="db_stats"),
      types.InlineKeyboardButton("⚠️ Reset Database", callback_data="reset_db"),
  )

  info_text = (
      f"⚡ **Full Admin Panel Connected!** ⚡\n\n"
      f"🌐 **Database:** `{db_name}`\n"
      f"🔗 **URL:** `{db_url}`\n\n"
      f"Select an option from the admin panel below:"
  )

  bot.send_message(chat_id, info_text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
  chat_id = call.message.chat.id

  if chat_id not in user_data and call.data != "start":
    bot.answer_callback_query(call.id, "Session expired. Send /start again.")
    return

  db_url = user_data[chat_id]["db_url"]

  if call.data == "gen_auto_key":
    bot.answer_callback_query(call.id)
    random_str = ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=8)
    )
    key_name = f"BKR-{random_str}"

    payload = {"key": key_name, "status": "active", "created_at": "2026"}
    res = requests.post(f"{db_url}/app_keys.json", json=payload)

    if res.status_code in [200, 201]:
      bot.send_message(
          chat_id,
          f"✅ **Auto-generated key saved successfully!**\n🔑 Key:"
          f" `{key_name}`",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(chat_id, "❌ Failed to save key.")

  elif call.data == "gen_custom_key":
    bot.answer_callback_query(call.id)
    sent = bot.send_message(
        chat_id,
        "Send your custom App Key text:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(sent, save_custom_key)

  elif call.data == "view_keys":
    bot.answer_callback_query(call.id)
    fetch_and_show_keys(chat_id)

  elif call.data == "delete_key_prompt":
    bot.answer_callback_query(call.id)
    sent = bot.send_message(
        chat_id,
        "Send the exact key text you want to delete:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(sent, delete_key_from_db)

  elif call.data == "set_update":
    bot.answer_callback_query(call.id)
    sent = bot.send_message(
        chat_id,
        "Send update details\nFormat: `VersionCode|Message`\nExample:"
        " `2|New update is available!`",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(sent, save_update_to_db)

  elif call.data == "del_update":
    bot.answer_callback_query(call.id)
    res = requests.delete(f"{db_url}/app_update.json")
    if res.status_code in [200, 204]:
      bot.send_message(chat_id, "✅ App update node deleted successfully.")
    else:
      bot.send_message(chat_id, "❌ Failed to delete update.")

  elif call.data == "toggle_maintenance":
    bot.answer_callback_query(call.id)
    sent = bot.send_message(
        chat_id,
        "Send maintenance status (`true` to lock app, `false` to unlock):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(sent, set_maintenance_mode)

  elif call.data == "set_notice":
    bot.answer_callback_query(call.id)
    sent = bot.send_message(chat_id, "Enter broadcast notice message for app:")
    bot.register_next_step_handler(sent, save_broadcast_notice)

  elif call.data == "db_stats":
    bot.answer_callback_query(call.id)
    try:
      res = requests.get(f"{db_url}/.json")
      data = res.json()
      keys_count = (
          len(data.get("app_keys", {}))
          if isinstance(data, dict) and data
          else 0
      )
      has_update = (
          "Yes"
          if isinstance(data, dict) and data and "app_update" in data
          else "No"
      )
      bot.send_message(
          chat_id,
          f"📊 **Database Statistics:**\n- Total Active Keys: `{keys_count}`\n-"
          f" Update Published: `{has_update}`",
          parse_mode="Markdown",
      )
    except Exception as e:
      bot.send_message(chat_id, f"❌ Error fetching stats: {str(e)}")

  elif call.data == "reset_db":
    bot.answer_callback_query(call.id)
    res = requests.delete(f"{db_url}/.json")
    if res.status_code in [200, 204]:
      bot.send_message(
          chat_id,
          "⚠️ **Database has been completely reset (emptied)!**",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(chat_id, "❌ Failed to reset database.")


def save_custom_key(msg):
  chat_id = msg.chat.id
  key_name = msg.text.strip()
  db_url = user_data[chat_id]["db_url"]

  payload = {"key": key_name, "status": "active", "created_at": "2026"}
  res = requests.post(f"{db_url}/app_keys.json", json=payload)

  if res.status_code in [200, 201]:
    bot.send_message(
        chat_id,
        f"✅ **Custom key saved successfully!**\n🔑 Key: `{key_name}`",
        parse_mode="Markdown",
    )
  else:
    bot.send_message(chat_id, "❌ Error saving key.")


def fetch_and_show_keys(chat_id):
  db_url = user_data[chat_id]["db_url"]
  try:
    res = requests.get(f"{db_url}/app_keys.json")
    data = res.json()

    if not data:
      bot.send_message(chat_id, "ℹ️ No keys found in database.")
      return

    key_list_str = ""
    for idx, (k_id, val) in enumerate(data.items(), 1):
      k_text = (
          val.get("key", "N/A") if isinstance(val, dict) else str(val)
      )
      key_list_str += f"{idx}. `{k_text}`\n"

    bot.send_message(
        chat_id,
        f"📋 **Existing Keys in Database:**\n\n{key_list_str}",
        parse_mode="Markdown",
    )
  except Exception as e:
    bot.send_message(chat_id, f"❌ Error: {str(e)}")


def delete_key_from_db(msg):
  chat_id = msg.chat.id
  target_key = msg.text.strip()
  db_url = user_data[chat_id]["db_url"]

  try:
    res = requests.get(f"{db_url}/app_keys.json")
    data = res.json()
    if not data:
      bot.send_message(chat_id, "❌ Database is empty.")
      return

    found = False
    for k_id, val in data.items():
      k_text = val.get("key", "") if isinstance(val, dict) else str(val)
      if k_text == target_key:
        requests.delete(f"{db_url}/app_keys/{k_id}.json")
        found = True
        break

    if found:
      bot.send_message(
          chat_id,
          f"✅ Key `{target_key}` deleted successfully.",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(chat_id, "❌ Key not found in database.")
  except Exception as e:
    bot.send_message(chat_id, f"❌ Error: {str(e)}")


def save_update_to_db(msg):
  chat_id = msg.chat.id
  text = msg.text.strip()
  db_url = user_data[chat_id]["db_url"]

  try:
    parts = text.split("|")
    payload = {
        "version_code": parts[0].strip(),
        "message": parts[1].strip(),
        "force_update": True,
    }
    res = requests.put(f"{db_url}/app_update.json", json=payload)
    if res.status_code in [200, 201, 204]:
      bot.send_message(chat_id, "✅ App update published successfully!")
    else:
      bot.send_message(chat_id, "❌ Failed to save update.")
  except Exception:
    bot.send_message(
        chat_id, "❌ Wrong format! Use `VersionCode|Message` format."
    )


def set_maintenance_mode(msg):
  chat_id = msg.chat.id
  status = msg.text.strip().lower()
  db_url = user_data[chat_id]["db_url"]

  if status in ["true", "false"]:
    val = True if status == "true" else False
    requests.put(f"{db_url}/maintenance.json", json=val)
    bot.send_message(
        chat_id, f"✅ Maintenance mode successfully set to `{status}`."
    )
  else:
    bot.send_message(chat_id, "❌ Please send only `true` or `false`.")


def save_broadcast_notice(msg):
  chat_id = msg.chat.id
  notice_text = msg.text.strip()
  db_url = user_data[chat_id]["db_url"]

  payload = {"notice": notice_text, "active": True}
  res = requests.put(f"{db_url}/app_notice.json", json=payload)
  if res.status_code in [200, 201, 204]:
    bot.send_message(chat_id, "✅ Broadcast notice set in database!")
  else:
    bot.send_message(chat_id, "❌ Failed to save notice.")


print("English Admin Bot is running...")
bot.infinity_polling()
