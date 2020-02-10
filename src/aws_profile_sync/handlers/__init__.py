"""This module contains handlers for the various supported URLs."""
from .ssh_git import SSHGitHandler

__all__ = ["SSHGitHandler"]


def find_handler(url):
    for handler in __all__:
        # Get the symbol for handler
        mod = globals()[handler]
        # Ask handler if it can handle the url
        if getattr(mod, "can_handle")(url):
            return mod
    return None
