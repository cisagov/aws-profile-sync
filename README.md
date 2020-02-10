# aws-profile-sync ☁️🧻🚰 #

[![GitHub Build Status](https://github.com/cisagov/aws-profile-sync/workflows/build/badge.svg)](https://github.com/cisagov/aws-profile-sync/actions)
[![Coverage Status](https://coveralls.io/repos/github/cisagov/aws-profile-sync/badge.svg?branch=develop)](https://coveralls.io/github/cisagov/aws-profile-sync?branch=develop)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/cisagov/aws-profile-sync.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/aws-profile-sync/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/cisagov/aws-profile-sync.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/aws-profile-sync/context:python)
[![Known Vulnerabilities](https://snyk.io/test/github/cisagov/aws-profile-sync/develop/badge.svg)](https://snyk.io/test/github/cisagov/aws-profile-sync)

`aws-profile-sync` is a command line utility that simplifies the synchronization
of
[AWS credential profiles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
across groups of users.

## Installation ##

From source:

```console
git clone https://github.com/cisagov/aws-profile-sync.git
cd aws-profile-sync
pip install -r requirements.txt
```

## Usage ##

The utility reads a credentials file looking for magic `#!aws-profile-sync` comments.
It will then fetch the remote content and intelligently integrate it into a new
credentials file.

```gitconfig
[cool-user]
aws_access_key_id = XXXXXXXXXXXXXXXXXXXX
aws_secret_access_key = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

#!profile-sync ssh://git@github.com/aceofspades/aws-profiles.git branch=master filename=roles -- source_profile=cool-user role_session_name=lemmy-is-god mfa_serial=arn:aws:iam::123456789012:mfa/ian.kilmister

# This line will get replaced

#!profile-sync-stop

# These lines won't be modified by the utility.
# That was a great time, the summer of '71 - I can't remember it, but I'll never forget it!.
```

The utility will replace all the content between the `#!aws-profile-sync` and
`#!aws-profile-sync-stop` lines in the above example.  To do this it will:

- Clone the repository that lives at `git@github.com/aceofspades/aws-profiles.git`.
- Switch to the `master` branch.
- Read the file `roles`.
- Override and replace any values specified after the `--` in the magic line.

A copy of your previous `credentials` file is stored next to it as `credentials.backup`.

For detailed usage instructions see: `aws-profile-sync --help`

## Contributing ##

We welcome contributions!  Please see [here](CONTRIBUTING.md) for
details.

## License ##

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain within the United States, and
copyright and related rights in the work worldwide are waived through
the [CC0 1.0 Universal public domain
dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0
dedication. By submitting a pull request, you are agreeing to comply
with this waiver of copyright interest.
