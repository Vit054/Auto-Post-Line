"""Send today's image to LINE recipients via Messaging API multicast.

Reads the committed image from its public raw.githubusercontent.com URL and
pushes it to every userId listed in LINE_USER_IDS (comma/newline separated).
"""
from __future__ import annotations

import os
import time

import requests

MULTICAST = "https://api.line.me/v2/bot/message/multicast"


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    ids = [
        x.strip()
        for x in os.environ.get("LINE_USER_IDS", "").replace("\n", ",").split(",")
        if x.strip()
    ]
    if not ids:
        print("LINE_USER_IDS is empty; nothing to send.")
        return

    repo = os.environ["GITHUB_REPOSITORY"]            # owner/name
    ref = os.environ.get("GITHUB_REF_NAME", "main")
    path = os.environ["IMAGE_PATH"]
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"

    # raw CDN can lag a few seconds behind the push — wait for it
    confirmed = False
    for i in range(20):
        try:
            if requests.head(url, timeout=15).status_code == 200:
                confirmed = True
                break
        except requests.RequestException as e:
            print(f"head check error: {e}")
        print(f"waiting for image to be live ({i + 1}/20)...")
        time.sleep(6)
    if not confirmed:
        print(f"WARNING: image URL not confirmed live, sending anyway: {url}")
    print(f"Image URL: {url}")

    message = {"type": "image", "originalContentUrl": url, "previewImageUrl": url}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for i in range(0, len(ids), 500):  # multicast accepts up to 500 ids per call
        batch = ids[i:i + 500]
        r = requests.post(
            MULTICAST,
            headers=headers,
            json={"to": batch, "messages": [message]},
            timeout=30,
        )
        print(f"LINE response {r.status_code}: {r.text[:300]}")
        r.raise_for_status()

    print(f"Sent to {len(ids)} recipient(s).")


if __name__ == "__main__":
    main()
