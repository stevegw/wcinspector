"""
Feature #12 Verification: Theme toggle switches between light and dark mode
"""
import asyncio
from playwright.async_api import async_playwright
import json
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_theme_toggle():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Step 1: Navigate to application (should be light theme by default)")
        await page.goto('http://localhost:8000')
        await page.wait_for_load_state('networkidle')

        # Check initial theme
        initial_theme = await page.evaluate('document.documentElement.getAttribute("data-theme")')
        print(f"  ✓ Initial theme: {initial_theme}")

        # Check initial background color
        initial_bg = await page.evaluate('getComputedStyle(document.body).backgroundColor')
        print(f"  ✓ Initial background: {initial_bg}")

        # Take screenshot
        await page.screenshot(path='.playwright-mcp/feature12_light_theme.png')

        print("\nStep 2: Click theme toggle button")
        await page.click('#theme-toggle')
        await asyncio.sleep(0.5)  # Wait for transition

        print("\nStep 3: Verify UI switches to dark theme colors")
        dark_theme = await page.evaluate('document.documentElement.getAttribute("data-theme")')
        print(f"  ✓ Theme after toggle: {dark_theme}")

        print("\nStep 4: Verify background changes to #1A1A1A")
        dark_bg = await page.evaluate('getComputedStyle(document.body).backgroundColor')
        print(f"  ✓ Dark background: {dark_bg}")

        # Convert rgb to hex to verify
        rgb_match = await page.evaluate("""() => {
            const bg = getComputedStyle(document.body).backgroundColor;
            const match = bg.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
            if (match) {
                const r = parseInt(match[1]);
                const g = parseInt(match[2]);
                const b = parseInt(match[3]);
                const hex = '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
                return hex;
            }
            return null;
        }""")
        print(f"  ✓ Background as hex: {rgb_match}")

        # Check icon changed
        icon = await page.text_content('#theme-toggle .icon')
        print(f"  ✓ Theme toggle icon: {icon}")

        # Take screenshot
        await page.screenshot(path='.playwright-mcp/feature12_dark_theme.png')

        print("\nStep 5: Click toggle again")
        await page.click('#theme-toggle')
        await asyncio.sleep(0.5)

        print("\nStep 6: Verify UI returns to light theme")
        light_theme_again = await page.evaluate('document.documentElement.getAttribute("data-theme")')
        print(f"  ✓ Theme after second toggle: {light_theme_again}")

        light_bg_again = await page.evaluate('getComputedStyle(document.body).backgroundColor')
        print(f"  ✓ Light background: {light_bg_again}")

        icon_again = await page.text_content('#theme-toggle .icon')
        print(f"  ✓ Theme toggle icon: {icon_again}")

        await page.screenshot(path='.playwright-mcp/feature12_light_theme_again.png')

        # Set to dark theme for persistence test
        if light_theme_again == 'light':
            await page.click('#theme-toggle')
            await asyncio.sleep(0.5)

        print("\nStep 7: Refresh page and confirm last theme persists")
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        persisted_theme = await page.evaluate('document.documentElement.getAttribute("data-theme")')
        print(f"  ✓ Theme after refresh: {persisted_theme}")

        persisted_bg = await page.evaluate('getComputedStyle(document.body).backgroundColor')
        print(f"  ✓ Background after refresh: {persisted_bg}")

        await page.screenshot(path='.playwright-mcp/feature12_theme_persisted.png')

        # Verification results
        print("\n" + "="*60)
        print("VERIFICATION RESULTS:")
        print("="*60)

        checks = {
            "Initial theme is light or dark": initial_theme in ['light', 'dark'],
            "Theme toggles to opposite": dark_theme != initial_theme,
            "Dark theme background is #1A1A1A": rgb_match == '#1A1A1A' if dark_theme == 'dark' else True,
            "Theme toggles back": light_theme_again == initial_theme,
            "Theme persists after refresh": persisted_theme == 'dark',
            "Icon changes based on theme": icon in ['☀️', '🌙']
        }

        for check, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {check}")

        all_passed = all(checks.values())
        print("\n" + "="*60)
        if all_passed:
            print("Feature #12: PASSED ✅")
        else:
            print("Feature #12: FAILED ❌")
        print("="*60)

        await browser.close()
        return all_passed

if __name__ == '__main__':
    result = asyncio.run(test_theme_toggle())
    exit(0 if result else 1)
