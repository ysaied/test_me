import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

from playwright.async_api import async_playwright, Error as PlaywrightError

BASE_DIR = Path(__file__).resolve().parent.parent
URL_DIR = Path(os.environ.get("URL_DIR", BASE_DIR / "urls")).resolve()
LOG_DIR = Path(os.environ.get("LOG_DIR", BASE_DIR / "logs")).resolve()
LOOP_DELAY = int(os.environ.get("LOOP_DELAY", "60"))
NAVIGATION_TIMEOUT_MS = int(os.environ.get("PLAYWRIGHT_TIMEOUT_MS", "15000"))

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "summary.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def discover_url_files(directory: Path) -> List[Path]:
    if not directory.exists():
        logging.warning("URL directory '%s' does not exist", directory)
        return []
    return sorted(p for p in directory.rglob("*url*.txt") if p.is_file())


def load_urls(files: Iterable[Path]) -> List[str]:
    seen = set()
    urls: List[str] = []
    for file_path in files:
        try:
            for line in file_path.read_text().splitlines():
                url = line.strip()
                if not url or url.startswith("#"):
                    continue
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
        except OSError as exc:
            logging.error("Failed to read %s: %s", file_path, exc)
    return urls


def condense_reason(reason: str) -> str:
    if not reason:
        return ""
    head = reason.strip().splitlines()[0].strip()
    return head.rstrip(":")


async def check_url(page, url: str) -> Tuple[bool, str]:
    try:
        response = await page.goto(url, wait_until="load", timeout=NAVIGATION_TIMEOUT_MS)
        if response is not None and response.status >= 400:
            return False, f"HTTP {response.status}"
        await page.wait_for_load_state("load")
        return True, "ok"
    except PlaywrightError as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return False, str(exc)


async def process_urls(urls: List[str]) -> Tuple[int, List[Tuple[str, str]]]:
    if not urls:
        logging.info("No URLs found. Waiting for new files...")
        return 0, []

    failed: List[Tuple[str, str]] = []
    success = 0

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        for url in urls:
            ok, reason = await check_url(page, url)
            if ok:
                success += 1
                logging.info("SUCCESS %s", url)
            else:
                short_reason = condense_reason(reason)
                failed.append((url, short_reason))
                logging.warning("FAILED %s", url)
        await page.close()
        await context.close()
        await browser.close()

    return success, failed


def append_summary(success: int, failed_count: int) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = (
        f"[{timestamp}]\n" f"Success: {success} URLs\n" f"Failed: {failed_count} URLs\n\n"
    )
    try:
        with LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(summary)
    except OSError as exc:
        logging.error("Unable to write summary log: %s", exc)


async def main() -> None:
    logging.info("Starting headless URL runner")
    logging.info("URL directory: %s", URL_DIR)
    logging.info("Log directory: %s", LOG_DIR)
    logging.info("Loop delay: %s seconds", LOOP_DELAY)

    while True:
        url_files = discover_url_files(URL_DIR)
        urls = load_urls(url_files)
        success, failed = await process_urls(urls)
        append_summary(success, len(failed))

        if failed:
            logging.info("Loop complete: %s success, %s failed", success, len(failed))
            for url, reason in failed:
                logging.info("Failure detail: %s (%s)", url, reason)
        else:
            logging.info("Loop complete: %s success, 0 failed", success)

        try:
            await asyncio.sleep(LOOP_DELAY)
        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:  # pragma: no cover - manual interruption
            logging.info("Received keyboard interrupt. Exiting loop.")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Stopped by user")
