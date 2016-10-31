import os
import logging
import subprocess

log = logging.getLogger(__name__)


class Updater:
    def __init__(self):
        print("==============================")
        log.info("Keeping the bot up to date...")
        cmd = "git pull"
        subprocess.check_call(cmd.split())
        print("==============================")
