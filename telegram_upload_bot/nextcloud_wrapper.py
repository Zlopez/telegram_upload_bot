"""
Nextcloud wrapper using nextcloud-api-wrapper.
"""
from typing import Optional, List

import arrow
import nextcloud

NEXTCLOUD_TIME_FORMAT="ddd, DD MMM YYYY HH:mm:ss ZZZ"


class Nextcloud:
    """
    Nextcloud class for communicating with nextcloud server.
    """
    # private nextcloud.Nextcloud object
    _nextcloud: nextcloud.NextCloud = None
    newest_file_timestamp: arrow.Arrow = None

    def __init__(
            self,
            url: str,
            username: str,
            password: str,
            timestamp: Optional[arrow.Arrow]
    ) -> None:
        """
        Initializes the Nextcloud instance.

        Params:
          url: URL to nextcloud server
          username: User to use on nextcloud server
          password: Password for the user
          timestamp: Timestamp of the currently known newest file on server
        """
        self._nextcloud = nextcloud.NextCloud(
            url,
            user=username,
            password=password
        )
        self.newest_file_timestamp = timestamp

    def collect_new_files(self, path: str, timestamp: Optional[arrow.Arrow]) -> List[str]:
        """
        Collect all files in the path that are newer than timestamp.

        Params:
          path: Path on the nextcloud server
          timestamp: Timestamp to from to look for newer files
        """
        files: List[bytes] = []
        folder = self._nextcloud.get_folder(path)
        for file in folder.list():
            last_modified = arrow.get(file.last_modified, NEXTCLOUD_TIME_FORMAT)
            if not timestamp:
                files.append(file.fetch_file_content())
            elif last_modified > timestamp:
                if last_modified > self.newest_file_timestamp:
                    self.newest_file_timestamp = last_modified
                files.append(file.fetch_file_content())

        return files