"""
Feature #18 Verification: Loading indicator shows during AI processing
"""
import asyncio
from playwright.async_api import async_playwright
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_loading_indicator():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Feature #18: Loading indicator shows during AI processing")
        print("=" * 60)

        print("\nStep 1: Enter a question in input field")
        await page.goto('http://localhost:8000')
        await page.wait_for_load_state('networkidle')
        print("  ✓ Application loaded")

        # Enter a question
        test_question = "TEST_LOADING_INDICATOR_18"
        await page.fill('#question-input', test_question)
        print(f"  ✓ Question entered: {test_question}")

        await page.screenshot(path='.playwright-mcp/feature18_question_entered.png')

        # Check initial state
        loading_visible_before = await page.is_visible('#loading-state')
        submit_disabled_before = await page.is_disabled('#submit-btn')
        print(f"  Initial loading visible: {loading_visible_before}")
        print(f"  Initial submit disabled: {submit_disabled_before}")

        print("\nStep 2: Click submit button")

        # Start monitoring for loading state to appear
        loading_promise = page.wait_for_selector('#loading-state:not(.hidden)', timeout=5000)

        # Click submit
        await page.click('#submit-btn')
        print("  ✓ Submit button clicked")

        # Immediately check if button is disabled
        await asyncio.sleep(0.05)  # Very brief wait for DOM update
        submit_disabled_immediately = await page.is_disabled('#submit-btn')

        print("\nStep 3: Verify loading spinner or indicator appears immediately")

        try:
            # Wait for loading state to appear
            await loading_promise
            loading_visible_during = True
            print("  ✓ Loading state appeared")
        except:
            loading_visible_during = False
            print("  ✗ Loading state did not appear")

        # Take screenshot during loading
        await asyncio.sleep(0.3)

        # Check if loading is still visible
        loading_still_visible = await page.is_visible('#loading-state:not(.hidden)')

        # Get loading text (even if loading is gone, check what was there)
        loading_text = await page.text_content('#loading-state')
        print(f"  Loading text: '{loading_text.strip()}'")
        print(f"  Loading still visible: {loading_still_visible}")

        await page.screenshot(path='.playwright-mcp/feature18_loading_shown.png')

        print("\nStep 4: Verify submit button becomes disabled")
        submit_disabled_during = submit_disabled_immediately or await page.is_disabled('#submit-btn')
        print(f"  Submit button disabled: {submit_disabled_during}")

        # Check for spinner animation or visual indicator
        has_spinner = await page.locator('#loading-state .spinner-large').count() > 0
        print(f"  Has spinner element: {has_spinner}")

        print("\nStep 5: Confirm loading indicator disappears when answer arrives")

        # Wait for answer to appear OR error state (loading should disappear)
        try:
            # Wait for either answer or error to appear
            await page.wait_for_selector('#answer-display:not(.hidden), #error-state:not(.hidden)', timeout=15000)
            answer_or_error_visible = True

            # Check which one appeared
            answer_visible = await page.is_visible('#answer-display:not(.hidden)')
            error_visible = await page.is_visible('#error-state:not(.hidden)')

            if answer_visible:
                print("  ✓ Answer displayed")
            elif error_visible:
                print("  ✓ Error state displayed (response completed)")
                answer_or_error_visible = True
        except:
            answer_or_error_visible = False
            print("  ✗ Neither answer nor error appeared in time")

        # Check loading state is now hidden
        loading_visible_after = await page.is_visible('#loading-state:not(.hidden)')
        print(f"  Loading visible after answer: {loading_visible_after}")

        # Check submit button is re-enabled
        submit_disabled_after = await page.is_disabled('#submit-btn')
        print(f"  Submit button disabled after answer: {submit_disabled_after}")

        await page.screenshot(path='.playwright-mcp/feature18_answer_displayed.png')

        # Verification summary
        print("\n" + "=" * 60)
        print("VERIFICATION RESULTS:")
        print("=" * 60)

        checks = {
            "Loading not visible initially": not loading_visible_before,
            "Submit enabled initially": not submit_disabled_before,
            "Loading appears on submit": loading_visible_during,
            "Submit disabled during loading": submit_disabled_during,
            "Loading text shown": len(loading_text.strip()) > 0,
            "Response completes (answer or error)": answer_or_error_visible,
            "Loading hidden after response": not loading_visible_after,
            "Submit re-enabled after response": not submit_disabled_after
        }

        for check, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {check}")

        all_passed = all(checks.values())
        print("\n" + "=" * 60)
        if all_passed:
            print("Feature #18: PASSED ✅")
        else:
            print("Feature #18: FAILED ❌")
        print("=" * 60)

        await browser.close()
        return all_passed

if __name__ == '__main__':
    result = asyncio.run(test_loading_indicator())
    exit(0 if result else 1)
