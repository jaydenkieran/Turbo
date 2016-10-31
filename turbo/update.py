import os
import logging
import git
import sys

log = logging.getLogger(__name__)


class Updater:
    def __init__(self):
        directory = os.getcwd()
        log.debug("Using {} as updater path".format(directory))
        try:
            try:
                self.repo = git.Repo(directory)
            except git.exc.InvalidGitRepositoryError:
                raise AssertionError("Not a valid git repository")

            assert not self.repo.bare, "Current git repository is bare"
            assert not self.repo.is_dirty(), "The repository is dirty"

            try:
                self.remote = self.repo.remotes['origin']
            except:
                raise AssertionError("The remote 'origin' does not exist")

            assert self.remote.exists(), "The remote is not valid"
        except AssertionError as e:
            log.info("Skipping update script: {}".format(e))
            return

        pull = self.remote.pull()[0]  # Pull from remote repository
        flags = pull.flags
        log.debug("Pull result was: {} ({})".format(flags, pull.note))

        if flags == 4:
            log.info("The bot is up-to-date with the latest GitHub version.")
        elif flags == 64:
            log.info("The bot was updated to the latest version on GitHub. Please run the bot again.")
            os._exit(1)
        else:
            return
