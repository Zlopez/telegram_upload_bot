# telegram_upload_bot
Simple telegram bot to upload NextCloud files to chats

This bot is looking at folders on NextCloud server and
uploads any new file from the folder to specified telegram
chat. It currently only uploads images and videos.

## Quick start
1. Clone the repository
  `git clone https://github.com/Zlopez/telegram_upload_bot.git`

2. Create a python virtualenv
  `python -m venv .venv`
  
3. Create config file
  `cp config.toml.example config.toml`
  
4. Update the config file. See comments for more info.

5. Run the bot
  `python telegram_upload_bot/telegram_upload_bot.py`

---
**NOTE**

Before the first run you will either need to provide a timestamp file
or comment out the folders. Otherwise it will upload all the files in
folders to telegram chat.

---

## Configuration

The configuration is using [toml](https://en.wikipedia.org/wiki/TOML) format
and there is example in this repository.

The bot supports multiple configurations. You just need to start it with `--config`
parameter:

`python telegram_upload_bot/telegram_upload_bot.py --config <path_to_config>`
