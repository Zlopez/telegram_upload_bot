"""
This is a main source file for telegram_upload_bot.
"""
import io
import logging
import os
import sys
import tempfile
import time
from typing import Optional

import argparse
import arrow
import filetype
from moviepy.editor import VideoFileClip
from PIL import Image
import telegram
import toml

from nextcloud_wrapper import Nextcloud

CONFIG_FILE="config.toml"

TIMESTAMP_FILE = "timestamp"

# Limit for image is 10 MB
IMAGE_SIZE_LIMIT = 10485760

# Limit for video is 50 MB
VIDEO_SIZE_LIMIT = 52428800

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

# For debugging
#log.level = logging.DEBUG


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
        log.debug("Reading config '{}'".format(config))
        if os.path.isfile(config):
            return toml.load(config)

    else:
        log.debug("Reading config '{}'".format(CONFIG_FILE))
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
        if os.path.isfile(filename):
            with open(filename) as f:
                timestamp = f.readline()
                return arrow.Arrow.fromtimestamp(timestamp)
    else:
        if os.path.isfile(TIMESTAMP_FILE):
            with open(TIMESTAMP_FILE) as f:
                timestamp = f.readline()
                return arrow.Arrow.fromtimestamp(timestamp)

    return None


def write_timestamp(filename: str, time: arrow.Arrow) -> None:
    """
    Write current time as timestamp to file specified by filename.
    Use TIMESTAMP_FILE if filename is not specified.

    Params:
      filename: File containing the timestamp.
      timestamp: Time to write
    """
    if filename:
        with open(filename, "w") as f:
            f.write(str(time.timestamp()))
    else:
        with open(TIMESTAMP_FILE, "w") as f:
            f.write(str(time.timestamp()))


if __name__ == "__main__":
    log.debug("Parsing arguments '{}'".format(sys.argv[1:]))
    args = parse_arguments(sys.argv[1:])
    config = read_config(args.config)

    log.debug("Reading timestamp from file '{}'".format(config.get("timestamp_file")))
    timestamp = read_timestamp(config.get("timestamp_file"))
    log.info("Loaded timestamp '{}' from timestamp file '{}'".format(timestamp.humanize(), config.get("timestamp_file")))

    log.debug("Initializing nextcloud object")
    nextcloud = Nextcloud(
        config.get("nextcloud_url"),
        config.get("nextcloud_username"),
        config.get("nextcloud_password"),
        timestamp
    )
    log.debug("Initializing telegram bot")
    bot = telegram.Bot(token=config.get("bot_api_token"))

    for folder in config.get("folders").values():
        files = nextcloud.collect_new_files(folder.get("path"), timestamp)
        caption = (
            "Album: {}\n"
            "[Link na album]({})"
        ).format(folder.get("name"), folder.get("link"))
        for filename, file in files:
            try:
                if filetype.is_image(file):
                    image = Image.open(io.BytesIO(file))
                    image_bytes = io.BytesIO()
                    image.save(image_bytes, "jpeg")
                    log.debug("Size of the image: {} MB".format(
                        sys.getsizeof(image_bytes)/1024/1024
                    ))
                    if sys.getsizeof(image_bytes) > IMAGE_SIZE_LIMIT:
                        log.info("Image is bigger than telegram size limit. Resizing...")
                        while sys.getsizeof(image_bytes) > IMAGE_SIZE_LIMIT:
                            image = image.reduce(2)
                            image.save(image_bytes, "jpeg")
                        log.debug("New size of the image: {} MB".format(
                            sys.getsizeof(image_bytes)/1024/1024
                        ))
                    log.info("File '{}' is image. Uploading to telegram.".format(filename))
                    bot.send_photo(
                        config.get("telegram_chat_id"),
                        image_bytes.getvalue(),
                        caption=caption,
                        parse_mode=telegram.ParseMode.MARKDOWN_V2
                    )
                if filetype.is_video(file):
                    log.debug("Size of the video: {} MB".format(
                        sys.getsizeof(image_bytes)/1024/1024
                    ))
                    video = file
                    if sys.getsizeof(video) > VIDEO_SIZE_LIMIT:
                        log.info("Video file is bigger than telegram size limit. Resizing...")
                        clip = VideoFileClip(file)
                        while sys.getsizeof(video) > VIDEO_SIZE_LIMIT:
                            clip = clip.resize(0.5)
                            with tempfile.TemporaryFile() as tmp_file:
                                clip.write_videofile(tmp_file)

                                video = open(tmp_file, "rb").read()
                        log.debug(
                            "New size of video file: {} MB".format(
                                sys.getsizeof(video)/1024/1024)
                        )
                    log.info("File '{}' is video. Uploading to telegram.".format(filename))
                    bot.send_video(
                        config.get("telegram_chat_id"),
                        video,
                        caption=caption,
                        parse_mode=telegram.ParseMode.MARKDOWN_V2
                    )
            except telegram.error.RetryAfter:
                # If we send too much files let's wait a little
                log.info("Too much files sent at once. Wait for 30 seconds.")
                time.sleep(30)
            except telegram.error.BadRequest as exc:
                # If this happen let's try to send the file again as document
                # If this fails just continue with next file
                log.exception(exc)
                log.info("Error when sending file, let's try to send it again as document.")
                try:
                    bot.send_document(
                        config.get("telegram_chat_id"),
                        file,
                        filename=filename,
                        caption=caption,
                        parse_mode=telegram.ParseMode.MARKDOWN_V2
                    )
                except telegram.error.BadRequest as exc:
                    log.error("Couldn't upload the file, skip it.")
                    log.exception(exc)
                    continue

        log.info("All new files from '{}' uploaded!".format(folder.get("path")))

        # Write timestamp to file
        log.debug("Writing new timestamp '{}' to timestamp file '{}'".format(
            nextcloud.newest_file_timestamp.humanize(),
            config.get("timestamp_file"))
        )
        write_timestamp(config.get("timestamp_file"), nextcloud.newest_file_timestamp)
        log.info("Wrote timestamp '{}' to timestamp file '{}'".format(
            nextcloud.newest_file_timestamp.humanize(), config.get("timestamp_file"))
        )
