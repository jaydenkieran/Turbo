import os
import logging
import git

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
            log.debug("Pre-update checks failed: {}".format(e))
            return

        pull = self.remote.pull()  # Pull from remote repository
        print(pull.flags)
