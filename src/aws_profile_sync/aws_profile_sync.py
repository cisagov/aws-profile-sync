#!/usr/bin/env python

"""Synchronize AWS CLI named profiles from a remote source.

This utility will fetch shared named profiles from a remote source
and then update an aws credentials file.

EXIT STATUS
    This utility exits with one of the following values:
    0   Update was successful.
    >0  An error occurred.

Usage:
  aws-profile-sync [options]
  aws-profile-sync (-h | --help)

Options:
  -c --credentials-file=FILENAME    The credentials file to update.
                         [default: ~/.aws/credentials]
  -d --dry-run           Show what would be changed, but don't modify anything
                         on disk.
  -h --help              Show this message.
  --log-level=LEVEL      If specified, then the log level will be set to
                         the specified value.  Valid values are "debug", "info",
                         "warning", "error", and "critical". [default: info]
  -w --warn-missing      Treat missing overrides as a warning instead of an error.
"""

# Standard Python Libraries
import logging
from pathlib import Path
import shutil
import sys

# Third-Party Libraries
import docopt
from more_itertools import peekable
from schema import And, Schema, SchemaError, Use

from . import handlers
from ._version import __version__

MAGIC_START = "#!profile-sync "
MAGIC_STOP = "#!profile-sync-stop"
PROFILE_START = "["
SYNC_PATH = "sync"


def generate_profile(line_gen, config_overrides, missing_override_level=logging.ERROR):
    """Generate a profile block with applied overrides.

    Args:
        line_gen: A peekable generator that will yield lines of a single profile.
            The first line yielded must be the profile header in the form: [name]
            line_gen will be read until a new profile header is peeked or the end of
            file.
        config_overrides: A dictonary mapping configuration names to their values.
            Any matching configuration names read from the line_gen will be overriden
            with the assocated value from this dictionary.  Only overrides that match
            will be yielded by the generator.

    Yields:
        Modified lines read from line_gen.

    """
    # The first line is the profile name in brackets
    yield next(line_gen)
    try:
        # Read until the next profile start or EOF
        while not line_gen.peek().startswith(PROFILE_START):
            line = next(line_gen)
            # Output configurations after applying overrides
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if not value and key not in config_overrides:
                    logging.log(
                        missing_override_level,
                        f"No override provided for an empty external configuration line: {key}",
                    )
                    if missing_override_level >= logging.ERROR:
                        raise ValueError(f"Missing override: {key}")
                yield f"{key} = {config_overrides.get(key, value)}"
            else:
                # Comment or whitespace pass through
                yield line

    except StopIteration:
        pass
    return


def read_external(line_gen, config_overrides, missing_override_level=logging.ERROR):
    """Read an external source for profiles and apply configuration overrides.

    Args:
        line_gen: A peekable generator that will yield lines of one or more profiles.
        config_overrides: A dictonary mapping configuration names to their values.

    Yields:
        Modified lines read from line_gen.

    """
    try:
        while True:
            if line_gen.peek().startswith(PROFILE_START):
                for line in generate_profile(
                    line_gen,
                    config_overrides,
                    missing_override_level=missing_override_level,
                ):
                    yield line
            else:
                yield next(line_gen)
    except StopIteration:
        pass
    return


def parse_magic(line):
    """Parse a magic config line and return the associated parameters.

    Parses a magic line of the following form:

    #!profile-sync url [handler-param=value...] -- [config-override=value...]

    Args:
        line: A magic string containing a URL, handler-specific parameters, and a list
            of key / value configuration overrides.

    Returns:
        A tuple containing the URL, handler parameter dictonary, and a configuration
        overrides dictionary.

    """
    logging.debug(f"Parsing magic: {line}")
    if "--" in line:
        # Split the line into handler and override sections
        handler_line, overrides_line = line.split("--")
    else:
        handler_line = line
        overrides_line = ""
    # Split the line into terms
    handler_terms = handler_line.split()
    # Discard the magic
    handler_terms.pop(0)
    url = handler_terms.pop(0)
    # Remaining handler_terms are params to the handler
    handler_params = dict(map(lambda x: x.split("="), handler_terms))

    # Process override line
    override_terms = overrides_line.split()
    # Split remaining terms into key value pairs
    config_overrides = dict(map(lambda x: x.split("="), override_terms))

    return url, handler_params, config_overrides


def handle_magic(magic_line, work_path, missing_override_level=logging.ERROR):
    """Handle the magic line and route it to the correct fetcher.

    Args:
        magic_line: A magic string to handle.
        work_path: A directory where the handler can store state.

    Returns:
        A generator that will access the external resource referenced in the
        magic line.

    """
    url, handler_params, config_overrides = parse_magic(magic_line)
    logging.debug(f"Processing remote: {url}")
    clazz = handlers.find_handler(url)
    if not clazz:
        raise ValueError(f"Could not find a handler that can fetch: {url}")
    logging.debug(f"Using {clazz} to fetch external data.")
    # Instanciate the handler
    handler = clazz(work_path)
    external_profile_gen = peekable(handler.fetch(url, **handler_params))
    return read_external(external_profile_gen, config_overrides, missing_override_level)


def generate_credentials_file(credentials_file, missing_override_level=logging.ERROR):
    """Generate lines for a credentials file by expanding external references.

    Args:
        credentials_file: The credentials file to read.

    Returns:
        A generator that will return updated lines based on the input credentials file.

    """
    logging.info(f"Reading credentials file located at: {credentials_file}")
    in_magic_block = False
    work_path = credentials_file.parent / SYNC_PATH
    line_gen = (line for line in open(credentials_file))
    while True:
        try:
            line = next(line_gen)
        except StopIteration:
            break
        if line.startswith(MAGIC_START):
            yield line + "\n"
            for external_line in handle_magic(line, work_path, missing_override_level):
                yield external_line
                if not external_line.endswith("\n"):
                    yield "\n"
            yield "\n" + MAGIC_STOP + "\n"
            in_magic_block = True
            continue
        if line.startswith(MAGIC_STOP):
            in_magic_block = False
            continue
        if not in_magic_block:
            yield line


def main():
    """Set up logging and generate a new credentials file."""
    args = docopt.docopt(__doc__, version=__version__)
    # Validate and convert arguments as needed
    schema = Schema(
        {
            "--log-level": And(
                str,
                Use(str.lower),
                lambda n: n in ("debug", "info", "warning", "error", "critical"),
                error="Possible values for --log-level are "
                + "debug, info, warning, error, and critical.",
            ),
            str: object,  # Don't care about other keys, if any
        }
    )

    try:
        args = schema.validate(args)
    except SchemaError as err:
        # Exit because one or more of the arguments were invalid
        print(err, file=sys.stderr)
        return 1

    # Assign validated arguments to variables
    credentials_file = Path(args["--credentials-file"]).expanduser()
    dry_run = args["--dry-run"]
    log_level = args["--log-level"]
    missing_override_level = (
        logging.WARNING if args["--warn-missing"] else logging.ERROR
    )

    # Set up logging
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
    )

    if dry_run:
        # The user requested a dry-run.  Just output the new file to stdout
        logging.info("Dry run.  Outputting credentials file to standard out:")
        for line in generate_credentials_file(credentials_file, missing_override_level):
            sys.stdout.write(line)
    else:
        # Carefully craft a new credentials file on disk.
        temp_file = credentials_file.with_suffix(".temp")
        backup_file = credentials_file.with_suffix(".backup")
        logging.info(f"Writing new credentials file to: {temp_file}")
        with open(temp_file, "wt") as out:
            for line in generate_credentials_file(
                credentials_file, missing_override_level
            ):
                out.write(line)

        # If everything has succeeded we swap in the new file and backup the original
        logging.info(f"Backing up previous credentials file to: {backup_file}")
        shutil.move(credentials_file, backup_file)
        logging.info(f"Moving new credentials file to: {credentials_file}")
        shutil.move(temp_file, credentials_file)

    # Stop logging and clean up
    logging.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
