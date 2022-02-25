"""
This is a main source file for telegram_upload_bot.
"""
import os
import sys
from typing import Optional

import argparse
import arrow
import filetype
import telegram
import toml

from nextcloud_wrapper import Nextcloud

FILE="test.jpg"

CONFIG_FILE="config.toml"

TIMESTAMP_FILE = "timestamp"


def parse_arguments(args: list) -> argparse.Namespace:
    """
    Parse arguments for the script.

    Params:
      args:Application arguments to parse.

    Returns:
      Parsed arguments as argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        description="Simple telegram bot for image uploading."
    )

    parser.add_argument(
        "--config",
        help="Configuration file"
    )

    return parser.parse_args()


def read_config(config: str) -> dict:
    """
    Read config file. If none is provided it will try DEFAULT_CONFIG_FILE.

    Params:
      Path to config file.

    Returns:
      Parsed configuration as dict.

    Raises:
      RuntimeError: When no configuration file could be found.
    """
    if config:
        if os.path.isfile(config):
            return toml.load(config)

    else:
        if os.path.isfile(CONFIG_FILE):
            return toml.load(CONFIG_FILE)

    raise RuntimeError("No configuration file found.")


def read_timestamp(filename: str) -> Optional[arrow.Arrow]:
    """
    Read timestamp from file. If no file is found
    it returns None.

    Params:
      filename: File containing the timestamp.

    Returns:
      Arrow object created from the timestamp or None.
    """
    if filename:
        if os.path.isfile(config):
            with open(filename) as f:
                timestamp = f.readline()
                return arrow.Arrow.fromtimestamp(timestamp)
    else:
        if os.path.isfile(TIMESTAMP_FILE):
            with open(TIMESTAMP_FILE) as f:
                timestamp = f.readline()
                return arrow.Arrow.fromtimestamp(timestamp)

    return None


def write_timestamp(filename: str) -> None:
    """
    Write current time as timestamp to file specified by filename.
    Use TIMESTAMP_FILE if filename is not specified.

    Params:
      filename: File containing the timestamp.
    """
    if filename:
        with open(filename, "w") as f:
            timestamp = arrow.now().timestamp()
            f.write(str(timestamp))
    else:
        with open(TIMESTAMP_FILE, "w") as f:
            timestamp = arrow.now().timestamp()
            f.write(str(timestamp))


if __name__ == "__main__":
    args = parse_arguments(sys.argv[1:])
    config = read_config(args.config)

    timestamp = read_timestamp(config.get("timestamp_file"))

    nextcloud = Nextcloud(
        config.get("nextcloud_url"),
        config.get("nextcloud_username"),
        config.get("nextcloud_password")
    )
    bot = telegram.Bot(token=config.get("bot_api_token"))

    # Write timestamp to file
    write_timestamp(config.get("timestamp_file"))

    for folder in config.get("folders").values():
        files = nextcloud.collect_new_files(folder.get("path"), timestamp)
        caption = (
            "Album: {}\n"
            "[Link na album]({})"
        ).format(folder.get("name"), folder.get("link"))
        for file in files:
            try:
                if filetype.is_image(file):
                    bot.send_photo(
                        config.get("telegram_chat_id"),
                        file,
                        caption=caption,
                        parse_mode=telegram.ParseMode.MARKDOWN_V2
                    )
                if filetype.is_video(file):
                    bot.send_video(
                        config.get("telegram_chat_id"),
                        file,
                        caption=caption,
                        parse_mode=telegram.ParseMode.MARKDOWN_V2
                    )
            except telegram.error.RetryAfter:
                sleep(30)
