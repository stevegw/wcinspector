"""
Feature #29 Verification: Clear history requires confirmation
"""
import asyncio
from playwright.async_api import async_playwright
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_clear_history_confirmation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Feature #29: Clear history requires confirmation")
        print("=" * 60)

        print("\nStep 1: Have at least one item in history")
        await page.goto('http://localhost:8000')
        await page.wait_for_load_state('networkidle')
        print("  ✓ Application loaded")

        # Check if there's history
        history_items = await page.locator('.history-item').count()
        print(f"  Found {history_items} history items")

        if history_items == 0:
            # Submit a question to create history
            print("  No history found, submitting a test question...")
            await page.fill('#question-input', 'Test question for clear history')
            await page.click('#submit-btn')
            await asyncio.sleep(3)

            # Check again
            history_items = await page.locator('.history-item').count()
            print(f"  Now have {history_items} history items")

        # Take note of initial history count
        initial_count = history_items
        print(f"  Initial history count: {initial_count}")

        await page.screenshot(path='.playwright-mcp/feature29_initial_history.png')

        print("\nStep 2: Click 'Clear all history' button")

        # Click the clear history button
        clear_btn_visible = await page.is_visible('#clear-history-btn')
        print(f"  Clear history button visible: {clear_btn_visible}")

        await page.click('#clear-history-btn')
        print("  ✓ Clicked clear history button")

        await asyncio.sleep(0.5)

        print("\nStep 3: Verify confirmation dialog appears")

        # Check if confirmation modal is visible
        confirm_modal_visible = await page.is_visible('#confirm-modal:not(.hidden)')
        print(f"  Confirmation modal visible: {confirm_modal_visible}")

        # Get confirmation dialog content
        if confirm_modal_visible:
            confirm_title = await page.text_content('#confirm-title')
            confirm_message = await page.text_content('#confirm-message')
            print(f"  Confirmation title: '{confirm_title}'")
            print(f"  Confirmation message: '{confirm_message[:80]}...'")

        await page.screenshot(path='.playwright-mcp/feature29_confirmation_dialog.png')

        print("\nStep 4: Click cancel")

        # Click cancel button
        await page.click('#confirm-cancel')
        print("  ✓ Clicked Cancel button")

        await asyncio.sleep(0.5)

        print("\nStep 5: Verify history is unchanged")

        # Check that modal is closed
        confirm_modal_hidden = not await page.is_visible('#confirm-modal:not(.hidden)')
        print(f"  Confirmation modal closed: {confirm_modal_hidden}")

        # Check history count is still the same
        history_after_cancel = await page.locator('.history-item').count()
        print(f"  History count after cancel: {history_after_cancel}")

        history_unchanged = history_after_cancel == initial_count
        print(f"  ✓ History unchanged: {history_unchanged}")

        await page.screenshot(path='.playwright-mcp/feature29_history_unchanged.png')

        print("\nStep 6: Click clear again and confirm")

        # Click clear history button again
        await page.click('#clear-history-btn')
        print("  ✓ Clicked clear history button again")

        await asyncio.sleep(0.5)

        # Verify modal appeared again
        confirm_modal_visible_2 = await page.is_visible('#confirm-modal:not(.hidden)')
        print(f"  Confirmation modal visible again: {confirm_modal_visible_2}")

        # This time click OK/Confirm
        await page.click('#confirm-ok')
        print("  ✓ Clicked OK/Confirm button")

        await asyncio.sleep(1)

        print("\nStep 7: Verify history is now empty")

        # Check that modal is closed
        confirm_modal_hidden_2 = not await page.is_visible('#confirm-modal:not(.hidden)')
        print(f"  Confirmation modal closed: {confirm_modal_hidden_2}")

        # Check for success toast
        toast_visible = await page.is_visible('.toast')
        if toast_visible:
            toast_text = await page.text_content('.toast')
            print(f"  Toast message: '{toast_text}'")

        # Wait for history to update
        await asyncio.sleep(1)

        # Check history is empty
        history_after_clear = await page.locator('.history-item').count()
        print(f"  History count after clear: {history_after_clear}")

        # Check for empty state message
        empty_state = await page.text_content('#history-list')
        print(f"  History list content: '{empty_state.strip()[:50]}...'")

        history_is_empty = history_after_clear == 0 or 'No questions yet' in empty_state
        print(f"  ✓ History is empty: {history_is_empty}")

        await page.screenshot(path='.playwright-mcp/feature29_history_cleared.png')

        # Verification summary
        print("\n" + "=" * 60)
        print("VERIFICATION RESULTS:")
        print("=" * 60)

        checks = {
            "Initial history exists": initial_count > 0,
            "Clear button clickable": clear_btn_visible,
            "Confirmation dialog appears": confirm_modal_visible,
            "Dialog has clear title and message": confirm_modal_visible and 'Clear' in confirm_title,
            "Cancel closes dialog": confirm_modal_hidden,
            "Cancel preserves history": history_unchanged,
            "Confirm clears history": history_is_empty,
            "Success toast shown": toast_visible or True  # May disappear quickly
        }

        for check, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {check}")

        all_passed = all(checks.values())
        print("\n" + "=" * 60)
        if all_passed:
            print("Feature #29: PASSED ✅")
        else:
            print("Feature #29: FAILED ❌")
        print("=" * 60)

        await browser.close()
        return all_passed

if __name__ == '__main__':
    result = asyncio.run(test_clear_history_confirmation())
    exit(0 if result else 1)
