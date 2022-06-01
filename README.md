# YouTube-Archive-Sync

GitHub Action to archive YouTube channels by uploading their videos to [archive.org](https://archive.org).

## Getting Started

**1. [Fork this repository](https://github.com/Alyetama/yt-archive-sync/fork).**

**2. Create a database:**
  - **Option 1:**  MongoDB (recommended).
    - Self-hosted (see: [Alyetama/quick-MongoDB](https://github.com/Alyetama/quick-MongoDB) or [dockerhub image](https://hub.docker.com/_/mongo)).
    - Free database on [Atlas](https://www.mongodb.com/database/free).
  - **Option 2:** JSON bin (if you want a quick start).
    - Sign up to JSONBin [here](https://jsonbin.io/login).
    - Click on `VIEW MASTER KEY`, then copy the key.

**3. Add your *Archive.org* credentials to the repository's *Actions* secrets:**

  - `ARCHIVE_USERNAME`
  - `ARCHIVE_PASSWORD`

**4. Add a list of the channels you want to archive to the repository's *Actions* secrets:**

The `CHANNELS` secret should be formatted like this example:

```
CHANNEL_NAME: CHANNEL_URL
FOO: CHANNEL_URL
FOOBAR: CHANNEL_URL
SOME_CHANNEL: CHANNEL_URL
```

Don't add any quotes around the name or the URL, and make sure to keep one space between the colon and the URL.


**5. Add the database secret(s) to the repository's *Actions* secrets:**

If you picked **option 1 (MongoDB)**, add this additional secret:
  - `MONGODB_CONNECTION_STRING`

If you picked **option 2 (JSON bin)**, add this additional secret:
  - `JSONBIN_KEY`  


**6. Run the workflow under `Actions` manually with a `workflow_dispatch`, or wait for it to run automatically.**

That's it!


## Notes

- Information about the `MONGODB_CONNECTION_STRING` can be found [here](https://www.mongodb.com/docs/manual/reference/connection-string/).
- Jobs can run for a maximum of 6 hours, so if you're archiving a large channel, the job might die, but it will resume in a new job when it's scheduled to run.
