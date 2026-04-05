"""
Create a logged-in browser profile for a marketplace.

Usage:
    python scripts/create_browser_profile.py depop
    python scripts/create_browser_profile.py ebay
    python scripts/create_browser_profile.py mercari
    python scripts/create_browser_profile.py offerup

A Chromium window will open. Log in to the site, then press Enter here to save and exit.
"""

import asyncio
import os
import sys
from pathlib import Path

SITES = {
    "depop": "https://www.depop.com/login/",
    "ebay": "https://signin.ebay.com/",
    "mercari": "https://www.mercari.com/login/",
    "offerup": "https://offerup.com/login/",
}


async def main(platform: str) -> None:
    if platform not in SITES:
        print(f"Unknown platform '{platform}'. Choose from: {', '.join(SITES)}")
        sys.exit(1)

    profile_root = Path(os.getenv("BROWSER_USE_PROFILE_ROOT", "profiles"))
    profile_dir = (profile_root / platform).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    url = SITES[platform]
    print(f"\nOpening {platform} login page: {url}")
    print(f"Profile will be saved to: {profile_dir}\n")

    try:
        from browser_use import BrowserSession
        from browser_use.browser import BrowserProfile
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you activated .venv:  . .venv/bin/activate")
        sys.exit(1)

    profile = BrowserProfile(
        user_data_dir=str(profile_dir),
        headless=False,
        stealth=True,
    )
    session = BrowserSession(browser_profile=profile)

    try:
        await session.start()
        page = await session.get_current_page()
        await page.goto(url)
        print("Browser is open. Log in to the site now.")
        print("When done, press Enter here to save the profile and close...")
        await asyncio.get_event_loop().run_in_executor(None, input)
    finally:
        stop = getattr(session, "stop", None)
        if stop:
            await stop()

    print(f"\nProfile saved: {profile_dir}")
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
