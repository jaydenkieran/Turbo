import logging
import subprocess

log = logging.getLogger(__name__)


class Updater:
    def __init__(self):
        print("==============================")
        log.info("Keeping the bot up to date...")
        cmd = "git pull"
        print()
        subprocess.check_call(cmd.split())
        print()
        log.info("Any changes will be applied on the next bot restart")
        print("==============================")
