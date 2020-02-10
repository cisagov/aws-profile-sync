"""This module contains handlers for the various supported URLs."""
from .ssh_git import SSHGitHandler

__all__ = ["SSHGitHandler"]


def find_handler(url):
    """Find a handler that will support a URL.

    Args:
        url: The URL to find a handler for.

    Returns:
        If a handler is found a class will be returned, None otherwise.

    """
    for handler in __all__:
        # Get the symbol for handler
        mod = globals()[handler]
        # Ask handler if it can handle the url
        if getattr(mod, "can_handle")(url):
            return mod
    return None
