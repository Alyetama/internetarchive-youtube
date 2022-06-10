# Internetarchive-YouTube

[![Poetry-build](https://github.com/Alyetama/internetarchive-youtube/actions/workflows/poetry-build.yml/badge.svg)](https://github.com/Alyetama/internetarchive-youtube/actions/workflows/poetry-build.yml) [![Supported Python versions](https://img.shields.io/badge/Python-%3E=3.7-blue.svg)](https://www.python.org/downloads/) [![PEP8](https://img.shields.io/badge/Code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/) 

🚀 GitHub Action and CLI to archive YouTube channels by uploading the channel's videos to [archive.org](https://archive.org).

- 🧑‍💻 To use this tool as a command line interface (CLI), jump to [CLI: Getting Started](<#cli-getting-started-> "CLI: Getting Started").
- ⚡️ To use this tool as a GitHub Action, jump to [GitHub Action: Getting Started](<#github-action-getting-started-%EF%B8%8F> "GitHub Action: Getting Started").


## CLI: Getting Started 🧑‍💻

### Requirements:
- 🐍 [Python>=3.7](https://www.python.org/downloads/)

### ⬇️ Installation:
```sh
pip install internetarchive-youtube
```

### 🗃️ Backend database:
- [Create a backend database (or JSON bin)](<#%EF%B8%8F-creating-a-backend-database> "Creating a backend database") to track the download/upload overall progress.

- If you choose **MongoDB**, export the connection string as an environment variable:
```sh
export MONGODB_CONNECTION_STRING=mongodb://username:password@host:port
```

- If you choose **JSONBin**, export the master key as an environment variable:
```sh
export JSONBIN_KEY=xxxxxxxxxxxxxxxxx
```

### ⌨️ Usage:
```
usage: ia-yt [-h] [-p PRIORITIZE] [-s SKIP_LIST] [-f] [-t TIMEOUT] [-n] [-a] [-c CHANNELS_FILE] [-S] [-C]

optional arguments:
  -h, --help            show this help message and exit
  -p PRIORITIZE, --prioritize PRIORITIZE
                        Comma-separated list of channel names to prioritize
                        when processing videos
  -s SKIP_LIST, --skip-list SKIP_LIST
                        Comma-separated list of channel names to skip
  -f, --force-refresh   Refresh the database after every video (Can slow down
                        the workflow significantly, but is useful when running
                        multiple concurrent jobs)
  -t TIMEOUT, --timeout TIMEOUT
                        Kill the job after n hours (default: 5.5)
  -n, --no-logs         Don't print any log messages
  -a, --add-channel     Add a channel interactively to the list of channels to
                        archive
  -c CHANNELS_FILE, --channels-file CHANNELS_FILE
                        Path to the channels list file to use if the
                        environment variable `CHANNELS` is not set (default:
                        ~/.yt_channels.txt)
  -S, --show-channels   Show the list of channels in the channels file
  -C, --create-collection
                        Creates/appends to the backend database from the
                        channels list
```

---

## GitHub Action: Getting Started ⚡️

1. **[Fork this repository](https://github.com/Alyetama/yt-archive-sync/fork).**
2. **[Create a backend database (or JSON bin)](<#%EF%B8%8F-creating-a-backend-database> "Creating a backend database").**
3. **Add your *Archive.org* credentials to the repository's *Actions* secrets:**
  - `ARCHIVE_USER_EMAIL`
  - `ARCHIVE_PASSWORD`

4. **Add a list of the channels you want to archive to the repository's Actions secrets:**

The `CHANNELS` secret should be formatted like this example:

```
CHANNEL_NAME: CHANNEL_URL
FOO: CHANNEL_URL
FOOBAR: CHANNEL_URL
SOME_CHANNEL: CHANNEL_URL
```

Don't add any quotes around the name or the URL, and make sure to keep one space between the colon and the URL.


5. **Add the database secret(s) to the repository's *Actions* secrets:**

If you picked **option 1 (MongoDB)**, add this additional secret:
  - `MONGODB_CONNECTION_STRING`

If you picked **option 2 (JSON bin)**, add this additional secret:
  - `JSONBIN_KEY`  


6. **Run the workflow under `Actions` manually with a `workflow_dispatch`, or wait for it to run automatically.**

That's it!


## 🏗️ Creating A Backend Database

- **Option 1:**  MongoDB (recommended).
  - Self-hosted (see: [Alyetama/quick-MongoDB](https://github.com/Alyetama/quick-MongoDB) or [dockerhub image](https://hub.docker.com/_/mongo)).
  - Free database on [Atlas](https://www.mongodb.com/database/free).
- **Option 2:** JSON bin (if you want a quick start).
  - Sign up to JSONBin [here](https://jsonbin.io/login).
  - Click on `VIEW MASTER KEY`, then copy the key.

---

## 📝 Notes

- Information about the `MONGODB_CONNECTION_STRING` can be found [here](https://www.mongodb.com/docs/manual/reference/connection-string/).
- Jobs can run for a maximum of 6 hours, so if you're archiving a large channel, the job might die, but it will resume in a new job when it's scheduled to run.
- Instead of raw text, you can pass a file path or a file URL with a list of channels formatted as `CHANNEL_NAME: CHANNEL_URL` or in JSON format `{"CHANNEL_NAME": "CHANNEL_URL"}`.
