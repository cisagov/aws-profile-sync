"""A Git repository over secure shell handler."""

# Standard Python Libraries
import logging
from pathlib import Path
import subprocess  # nosec: Security of subprocess has been considered


class SSHGitHandler(object):
    """A Git repository over secure shell handler.

    This class can clone or update an existing clone of a remote repository that is
    served over ssh.
    """

    CLONE_PATH = Path("git")

    @staticmethod
    def can_handle(url):
        """Determine if this class can handle a specified URL.

        Args:
            url: A URL of any format.

        Returns:
            True if the URL can be handled.  False otherwise.

        """
        return url.startswith("ssh://") and url.endswith(".git")

    def __init__(self, work_path):
        """Instanciate a new SSHGitHandler.

        The class will create a directory structure it requires to store cloned
        repositories within the working path.

        Args:
            work_path: A pathlib.Path pointing to a work directory.

        """
        super(SSHGitHandler, self).__init__()
        self.work_path = work_path / SSHGitHandler.CLONE_PATH
        self.work_path.mkdir(parents=True, exist_ok=True)

    def fetch(self, url, branch="master", filename="roles"):
        """Generate lines from the retrieved repository file.

        Args:
            url: A git-style URL pointing to a repository with profile formatted files
            repo_file: The file to read from the repository.

        Yields:
            Lines read from the specified repository file.

        Raises:
            subprocess.CalledProcessError: If a subprocess returns a non-zero exit code.

        """
        repo_name = url.split("/")[-1].split(".")[0]
        repo_path = self.work_path / repo_name
        read_file = repo_path / filename

        if repo_path.exists():
            logging.info(f"Pulling {url}")
            subprocess.run(["git", "pull"], check=True, cwd=repo_path)  # nosec
        else:
            logging.info(f"Cloning {url}")
            subprocess.run(  # nosec
                ["git", "clone", url], check=True, cwd=self.work_path
            )
        # Switch to the requested branch
        logging.debug(f"Switching to branch {branch}")
        subprocess.run(["git", "switch", branch], check=True, cwd=repo_path)  # nosec

        logging.debug(f"Reading from repo: {read_file}")
        with read_file.open() as f:
            for line in f:
                yield line
        return
