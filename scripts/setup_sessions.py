#!/usr/bin/env python
"""
Playwright Session Warmup Utility

Use this script to manually log into marketplaces (Depop, eBay, OfferUp)
so that Browser Use can reuse the authenticated session for agents.
It launches a headed Chromium browser using patchright, lets you log in,
and then saves the profile.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path so we can import from backend
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from patchright.async_api import async_playwright
from backend.agents.browser_use_support import get_browser_profile_path

MARKETPLACES = {
    "depop": "https://www.depop.com/login",
    "ebay": "https://www.ebay.com/signin",
    "offerup": "https://offerup.com/login",
}


async def warmup_profile(platform: str) -> None:
    if platform not in MARKETPLACES:
        print(f"Unknown platform: {platform}. Valid options: {list(MARKETPLACES.keys())}")
        return

    url = MARKETPLACES[platform]
    profile_path = get_browser_profile_path(platform)

    # Ensure parent directory exists
    Path(profile_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Warming up profile for {platform.upper()} ---")
    print(f"Profile will be saved to: {profile_path}")
    print("Launching Chromium...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=False,
            # Common anti-bot args
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            viewport={"width": 1280, "height": 800},
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        # Mask automation
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        print(f"Navigating to {url} ...")
        await page.goto(url)

        print("\n" + "=" * 60)
        print("ACTION REQUIRED in the browser window:")
        print("1. Log in to your account")
        print("2. Solve any captchas (if asked)")
        print("3. Dismiss any initial popups")
        print("=" * 60)

        # Wait for user to manually complete login and press Enter
        await asyncio.to_thread(input, "\nPress Enter here in the terminal when you are fully logged in...")

        print("Saving profile and closing browser...")
        await browser.close()
        print(f"Profile for {platform} saved successfully.\n")


async def main() -> None:
    print("Marketplace Profile Setup Utility")
    print("---------------------------------")
    print("This script will open a browser window for each platform.")
    print("You will need to manually log in to save the session state.")

    for platform in MARKETPLACES:
        choice = input(f"\nDo you want to log into {platform}? (y/N): ").strip().lower()
        if choice in ("y", "yes"):
            await warmup_profile(platform)

    print("\nAll done. The agents will now use these profiles for Browser Use tasks.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)
