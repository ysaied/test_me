# Headless URL Runner

Dockerized Playwright + Chromium runner that continually checks a list of URLs and writes success/failure summaries.

## Project Layout
- `Dockerfile` – container definition based on `python:3.12-slim`
- `requirements.txt` – Python dependencies
- `scripts/runner.py` – Playwright automation loop
- `urls/top5_urls.txt` – default URL list bundled with the image
- `logs/` – created automatically at runtime

## Build the Image
```bash
docker build -t url-runner .
```

## Run with Bundled URLs
```bash
docker run --rm -it url-runner
```

## Provide Additional URL Files
Any file named `*url*.txt` in `/app/urls` is loaded on each loop. Mount extra files from the host:
```bash
docker run --rm -it \
  -v "$(pwd)/more_urls:/app/urls" \
  -v "$(pwd)/logs:/app/logs" \
  url-runner
```

The script merges all URLs (ignoring duplicates), visits each page in headless Chromium, then appends a summary to `/app/logs/summary.log`. It waits 60 seconds between loops and repeats until stopped.

### DNS Resolution
The container rewrites `/etc/resolv.conf` on startup so all lookups go through `8.8.8.8` and `8.8.4.4`. Override this by supplying your own entrypoint or adding `--dns` flags when running the container.

### TLS Handling
Playwright contexts launch with `ignore_https_errors=True`, allowing the runner to load HTTPS pages that use self-signed or otherwise invalid certificates.

### Playwright Fallback
If Playwright navigation fails, the script immediately retries the URL with an `aiohttp` GET request (with TLS verification disabled). A successful retry is logged as `SUCCESS_HTTP`, while failures from both attempts are recorded as errors.
