# yt-archive-sync

GitHub Action to archive YouTube channels by uploading their videos to [archive.org](https://archive.org).

## Getting Started

**1. [Fork this repository](https://github.com/Alyetama/yt-archive-sync/fork).**

**2. Create a MongoDB database:**
  - Self-hosted (see: [Alyetama/quick-MongoDB](https://github.com/Alyetama/quick-MongoDB) or [dockerhub image](https://hub.docker.com/_/mongo)).
  - Free database on [Atlas](https://www.mongodb.com/database/free).

**3. Add the following secrets to the repository's *Actions* secrets:**
  - `MONGODB_CONNECTION_STRING`
  - `ARCHIVE_USERNAME`
  - `ARCHIVE_PASSWORD`
  - `CHANNEL_NAME`

Information about the `MONGODB_CONNECTION_STRING` can be found [here](https://www.mongodb.com/docs/manual/reference/connection-string/). `CHANNEL_NAME` is the name of the channel you want to sync.

**4. On a local machine, run the following:**

```sh
git clone https://github.com/Alyetama/yt-archive-sync.git
cd yt-archive-sync

pip install "pymongo[srv]>=4.0.2" "python-dotenv>=0.20.0"

export MONGODB_CONNECTION_STRING="replace_with_connection_string"

python create_collection.py "replace_with_channel_url" "replace_with_channel_name"
```

**5. Run the workflow under `Actions` manually wuth a workflow_dispatch or wait for it to run automatically. That's it!**
