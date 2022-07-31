# Internetarchive-YouTube

[![Poetry-build](https://github.com/Alyetama/internetarchive-youtube/actions/workflows/poetry-build.yml/badge.svg)](https://github.com/Alyetama/internetarchive-youtube/actions/workflows/poetry-build.yml) [![Supported Python versions](https://img.shields.io/badge/Python-%3E=3.7-blue.svg)](https://www.python.org/downloads/) [![PEP8](https://img.shields.io/badge/Code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/) 

🚀 GitHub Action and CLI tool to archive YouTube channels by automatically uploading an entire YouTube channel to [archive.org](https://archive.org) in few clicks.

## 📌 Global Requirements

- All you need is an [Internet Archive account](https://archive.org/account/signup).

## 🔧 Usage

- ⚡️ To use this tool as a GitHub Action, jump to [GitHub Action: Getting Started](<#%EF%B8%8F-github-action-getting-started> "GitHub Action: Getting Started").
- 🧑‍💻 To use this tool as a command line interface (CLI), jump to [CLI: Getting Started](<#-cli-getting-started> "CLI: Getting Started").

---

### ⚡️ GitHub Action: Getting Started

<details>
  <summary>Using internetarchive-youtube as a GitHub Action instructions</summary>

1. **[Fork this repository](https://github.com/Alyetama/yt-archive-sync/fork).**

2. **Enable the workflows in your fork.**

<img src="https://i.imgur.com/J1udGei.jpeg"  width="720" alt=""> 
<img src="https://i.imgur.com/WhyFjWy.jpeg"  width="720" alt=""> 

3. **[Create a backend database (or JSON bin)](<#%EF%B8%8F-creating-a-backend-database> "Creating a backend database").**

4. **Add your *Archive.org* credentials to the repository's actions secrets:**
  - `ARCHIVE_USER_EMAIL`
  - `ARCHIVE_PASSWORD`

5. **Add a list of the channels you want to archive as a `CHANNELS` secret to the repository's actions secrets:**

The `CHANNELS` secret should be formatted like this example:

```YAML
CHANNEL_NAME: CHANNEL_URL
FOO: FOO_CHANNEL_URL
FOOBAR: FOOBAR_CHANNEL_URL
SOME_CHANNEL: SOME_CHANNEL_URL
```

Don't add any quotes around the name or the URL, and make sure to keep one space between the colon and the URL.

6. **Add the database secret(s) to the repository's *Actions* secrets:**

If you picked **option 1 (MongoDB)**, add this secret:
  - `MONGODB_CONNECTION_STRING`
The value of the secret is the database conneciton string.

If you picked **option 2 (JSON bin)**, add this additional secret:
  - `JSONBIN_KEY`  
The value of this secret is the *MASTER KEY* token you copied from JSONbin.

7. (optional) You can add command line options other than the defaults by creating a secret called `CLI_OPTIONS` and adding the options to the secret. See the [CLI: Getting Started](<#-cli-getting-started> "CLI: Getting Started") for a list of all the available options.

8. **Run the workflow under `Actions` manually, or wait for it to run automatically every 6 hours.**

That's it! 🎉

</details>


### 🧑‍💻 CLI: Getting Started

<details>
  <summary>Using internetarchive-youtube as a CLI tool instructions</summary>

#### Requirements:

- 🐍 [Python>=3.7](https://www.python.org/downloads/)

#### ⬇️ Installation:

```sh
pip install internetarchive-youtube
```

Then login to internetarchive:

```sh
ia configure
```

#### 🗃️ Backend database:

- [Create a backend database (or JSON bin)](<#%EF%B8%8F-creating-a-backend-database> "Creating a backend database") to track the download/upload overall progress.

- If you choose **MongoDB**, export the connection string as an environment variable:

```sh
export MONGODB_CONNECTION_STRING=mongodb://username:password@host:port

# or add it to your shell configuration file:
echo "MONGODB_CONNECTION_STRING=$MONGODB_CONNECTION_STRING" >> "$HOME/.$(basename $SHELL)rc"
source "$HOME/.$(basename $SHELL)rc"
```

- If you choose **JSONBin**, export the master key as an environment variable:

```sh
export JSONBIN_KEY=xxxxxxxxxxxxxxxxx

# or add it to your shell configuration file:
echo "JSONBIN_KEY=$JSONBIN_KEY" >> "$HOME/.$(basename $SHELL)rc"
source "$HOME/.$(basename $SHELL)rc"
```

#### ⌨️ Usage:

```
usage: ia-yt [-h] [-p PRIORITIZE] [-s SKIP_LIST] [-f] [-t TIMEOUT] [-n] [-a] [-c CHANNELS_FILE] [-S] [-C] [-m] [-T THREADS] [-k] [-i IGNORE_VIDEO_IDS]

options:
  -h, --help            show this help message and exit
  -p PRIORITIZE, --prioritize PRIORITIZE
                        Comma-separated list of channel names to prioritize when processing videos.
  -s SKIP_LIST, --skip-list SKIP_LIST
                        Comma-separated list of channel names to skip.
  -f, --force-refresh   Refresh the database after every video (Can slow down the workflow significantly, but is useful when running multiple concurrent
                        jobs).
  -t TIMEOUT, --timeout TIMEOUT
                        Kill the job after n hours (default: 5.5).
  -n, --no-logs         Don't print any log messages.
  -a, --add-channel     Add a channel interactively to the list of channels to archive.
  -c CHANNELS_FILE, --channels-file CHANNELS_FILE
                        Path to the channels list file to use if the environment variable `CHANNELS` is not set (default: ~/.yt_channels.txt).
  -S, --show-channels   Show the list of channels in the channels file.
  -C, --create-collection
                        Creates/appends to the backend database from the channels list.
  -m, --multithreading  Enables processing multiple videos concurrently.
  -T THREADS, --threads THREADS
                        Number of threads to use when multithreading is enabled. Defaults to the optimal maximum number of workers.
  -k, --keep-failed-uploads
                        Keep the files of failed uploads on the local disk.
  -i IGNORE_VIDEO_IDS, --ignore-video-ids IGNORE_VIDEO_IDS
                        Comma-separated list or a path to a file containing a list of video ids to ignore.
```

</details>

---

## 🏗️ Creating A Backend Database

<details>
  <summary>Creating A Backend Database instructions</summary>

- **Option 1:**  MongoDB (recommended).
  - Self-hosted (see: [Alyetama/quick-MongoDB](https://github.com/Alyetama/quick-MongoDB) or [dockerhub image](https://hub.docker.com/_/mongo)).
  - Free cloud database on [Atlas](https://www.mongodb.com/database/free).
- **Option 2:** JSON bin (if you want a quick start).
  - Sign up to JSONBin [here](https://jsonbin.io/login).
  - Click on `VIEW MASTER KEY`, then copy the key.
  
</details>


## 📝 Notes

- Information about the `MONGODB_CONNECTION_STRING` can be found [here](https://www.mongodb.com/docs/manual/reference/connection-string/).
- Jobs can run for a maximum of 6 hours, so if you're archiving a large channel, the job might die, but it will resume in a new job when it's scheduled to run.
- Instead of raw text, you can pass a file path or a file URL with a list of channels formatted as `CHANNEL_NAME: CHANNEL_URL`. You can also pass raw text or a file of the channels in JSON format `{"CHANNEL_NAME": "CHANNEL_URL"}`.
