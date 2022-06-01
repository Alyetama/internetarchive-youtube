# yt-archive-sync

GitHub Action to archive YouTube channels by uploading their videos to [archive.org](https://archive.org).

## Getting Started

**1. [Fork this repository](https://github.com/Alyetama/yt-archive-sync/fork).**

**2. Create a database:**
  - **Option 1:**  MongoDB (recommended).
    - Self-hosted (see: [Alyetama/quick-MongoDB](https://github.com/Alyetama/quick-MongoDB) or [dockerhub image](https://hub.docker.com/_/mongo)).
    - Free database on [Atlas](https://www.mongodb.com/database/free).
  - **Option 2:** JSON bin (if you want a quick start).
    - [JSONBIN.io](https://jsonbin.io/) (see below).

If you choose **option 1 (MongoDB)**, run the following code snippet on a local machine:

```sh
git clone https://github.com/Alyetama/yt-archive-sync.git
cd yt-archive-sync
pip install -r requirements.txt

export MONGODB_CONNECTION_STRING="replace_with_connection_string"

python create_collection.py -c "replace_with_channel_url" \
  -n "replace_with_channel_name" \
  --mongodb
```

If you choose **option 2 (local JSON file)**, run these lines instead:

- Sign up to JSONBin [here](https://jsonbin.io/login).
- Click on `VIEW MASTER KEY`, then copy the key.
- Open a terminal window, and run the following commands:

```sh
git clone https://github.com/Alyetama/yt-archive-sync.git
cd yt-archive-sync
pip install -r requirements.txt

export JSONBIN_KEY="REPLACE_ME"  # Replace with the master key you copied

python create_collection.py -c "replace_with_channel_url" \
  -n "replace_with_channel_name" \
  --jsonbin
```

**4. Add the following secrets to the repository's *Actions* secrets:**

  - `ARCHIVE_USERNAME`
  - `ARCHIVE_PASSWORD`
  - `CHANNEL_NAME`

If you're using **MongoDB (option 1)**, add this additional secret:
  - `MONGODB_CONNECTION_STRING`

If you're using **JSONBIN (option 2)**, add this additional secret:
  - `JSONBIN_KEY`  


**5. Run the workflow under `Actions` manually with a `workflow_dispatch` or wait for it to run automatically.**

That's it!


## Notes

- Information about the `MONGODB_CONNECTION_STRING` can be found [here](https://www.mongodb.com/docs/manual/reference/connection-string/).
- `CHANNEL_NAME` is the name of the channel you want to sync.
- If want to download another channel, simply run the `create_collection.py` line again, then replace the `CHANNEL_NAME` secret value.
