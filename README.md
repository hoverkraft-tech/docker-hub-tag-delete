# Docker Hub Image Tag Deleter

[![Tests](https://github.com/hoverkraft-tech/docker-hub-tag-delete/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/hoverkraft-tech/docker-hub-tag-delete/actions/workflows/tests.yml)

Schedule and handle the deletion of image tags on the [DockerHub](https://hub.docker.com).

A GitHub action is also included.

## Getting Started

1. Provide a list of tags in a JSON and/or Markdown file with a deletion date.
   See [Tag List](#tag-list) below.

2. Run via [cli](#running) or [GitHub Action](#github-action).

## Configuration

Configuration is handled using environment variables. The GitHub Action uses
inputs that set these. Refer to [GitHub Action](#github-action) below for
information about its configuration.

### Environment Variables

#### `DOCKERHUB_USERNAME`

__Required__

The username for authenticating with Docker Hub.

#### `DOCKERHUB_PASSWORD`

__Required__

The password or access token for authenticating with Docker Hub.

#### `DOCKERHUB_REPOSITORY`

__Required__

The name of the repository (image) on Docker Hub in the format of
`<namespace>/<name>`

#### `DATE_FORMAT`

Format the source date is in using standard the C standard.

See <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes>
for more information.

Default: `%B %d, %Y` (October 6, 2022)

#### `DOCKERHUB_API_BASE_URL`

The base URL of the Docker Hub API.

Default: _https://hub.docker.com/v2_

#### `JSON_FILE`

The relative path to a JSON file containing a list of tags and dates.

#### `MARKDOWN_FILE`

The relative path to a Markdown file containing a table with tags and dates.

#### `MARKDOWN_BEGIN_STRING`

A string that begins the Markdown table block with tags to parse.

#### `MARKDOWN_END_STRING`

A string that ends the Markdown table block with tags.

#### `MARKDOWN_TAG_COLUMN`

The column number that the tags are listed in.

Default: `1`

#### `MARKDOWN_DATE_COLUMN`

The table column number that the date is in.

Default: `2`

### Tag List

A source for tags and their deletion dates must be provided. This may be
provided in a coupld of ways - a JSON file and/or a Markdown table.

#### Tag List: JSON File

```json
[
  { "tags": ["1", "1.*"], "date": "October 1, 2022" },
  { "tags": ["2", "2.*"], "date": "November 13, 2023" }
]
```

* The JSON file should be a _list_ of _dictionaries_ with a `tag` and `date`
  key in each one.

* The value of `tags` should be a list of tag
  [patterns](https://docs.python.org/3/library/fnmatch.html) to match.
  The value of `date` should be a date in the [DATE_FORMAT](#date-format).

#### Tag List: Markdown Table

The tag list and deletion dates can be set in a Markdown table using the
following format:

```plain
<!-- BEGIN deletion_table -->
| Tag        | Deletion Date
| ---------- | ----------------------
| `1*`       | October 5, 2022
| `2.*`      | October 5, 2022
| `foobar`   | December 25, 2021
<!-- END deletion_table -->
```

* Use a BEGIN and END comment tag surrounding the table block in a Markdown
  document. These begin/end comment strings are configurable.

* Only lines that begin with a pipe (`|`) are parsed.

* The header names are irrelevant.

* The number of columns is irrelevant. (set the [tag](#markdown-tag-column)
  and [date](#markdown-date-column) column values if the tag/date aren't in the
  first two columns of the table.

* Two-column table with a list of grouped tags in the first column and the
  deletion date in the second column.

* The table column headers are customizable.

* The tag column may be a single tag or a list of comma-separated tags. The
  values can optionally be surrounded in backticks and can use wildcards.

* The date column should be a single date value in the configured
  [date format](#date-format).

## Running

Ensure the _required_ environment variables are set:

```shell
DOCKERHUB_REPOSITORY=foo/bar
DOCKERHUB_USERNAME=foo
DOCKERHUB_PASSWORD=hunter2
```

```shell
./hub-tag-delete.py
```

## GitHub Action

Basic usage:

```yaml
    - name: Docker Hub Tag Deleter
      uses: hoverkraft-tech/hub-tag-delete@v1
      with:
        dockerhub_username: ${{ secrets.DOCKERHUB_USERNAME }}
        dockerhub_password: ${{ secrets.DOCKERHUB_PASSWORD }}
        dockerhub_repository: foo/bar
        markdown_file: README.md
```

* The GitHub Action exposes all of the [environment
  variables](#environment-variables) as action inputs. At a minimum, the
  `dockerhub_username`, `dockerhub_password`, and `dockerhub_repository` must
  be set in addition to `markdown_file` and/or `json_file`.

* Use `v1` for the action version for now.

An example showing all inputs:

```yaml
    - name: Docker Hub Tag Deleter
      uses: hoverkraft-tech/hub-tag-delete@v1
      with:
        dockerhub_username: ${{ secrets.DOCKERHUB_USERNAME }}
        dockerhub_password: ${{ secrets.DOCKERHUB_PASSWORD }}
        dockerhub_repository: foo/bar
        dockerhub_api_base_url: https://hub.docker.com/v2
        date_format: '%B %d, %Y'
        json_file: images.json
        markdown_file: README.md
        markdown_begin_string: '<!-- BEGIN deletion_table -->'
        markdown_end_string: '<!-- END deletion_table -->'
        markdown_tag_column: 1
        markdown_date_column: 2
```

Refer to the `inputs` section of the [`action.yml`](action.yml) file for
more information.

See an example of using this in the
[hoverkraft-tech/docker-ansible](https://github.com/hoverkraft-tech/docker-ansible/)
repository.

## Developer Notes

### Local Python Environment

Create a virtual environment and activate it:

```shell
python -m venv env
. env/bin/activate
```

Install dependencies:

```shell
pip install -r requirements.txt
```

Set the [required environment variables](#environment-variables). See the
[Running](#running) section.

### Using Docker

To build a local image from the repository:

```shell
docker build -t hubclean:local .
```

To run the local image, pass along the required environment variables. For
example, using the `--env-file` option with the `docker run` command:

```shell
docker run --rm -v ${PWD}:/src -w /src --env-file env.local -it hubclean:local
```

Refer to the [Running](#running) section for an example of these required
[environment variables](#environment-variables).

To launch an interactive shell in the Docker container:

```shell
docker run --rm -v ${PWD}:/src -w /src --env-file env.local -it hubclean:local sh
```

To activate the Python virtual environment in the container:

```shell
. /var/hub-tag-delete-venv/bin/activate
```

* The script is located at `/usr/bin/hub-tag-delete.py`
* The Python virtual environment is under `/var/hub-tag-delete-venv`
* The image is based on Alpine Linux (via `python:3.x-alpine`)

## Branching Scheme

* `main` is the default branch that changes should be pulled into.
* `v1` is a "stable" branch.
* _tags_ are created by maintainer based on changes.

## TODO

* Improve error handling (v1)
* Improve output (v1)
* List on Marketplace once (v1) items are completed
* Improve [tests](tests/)
* CLI arguments in addition to existing env vars?
* GitLab registry support
* Build and publish image to Docker Hub (of this tool)
* Provide example GitLab pipeline config (using published image)
* Ongoing: general improvements

## Authors

* Forked from the initial work of Josh Beard, [joshbeard.me](https://joshbeard.me)
* Frederic Leger

## License

[BSD Zero Clause License (0BSD)](LICENSE)
