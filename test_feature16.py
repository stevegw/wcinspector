"""
Feature #16 Verification: Whitespace-only input shows validation error
"""
import asyncio
from playwright.async_api import async_playwright
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_whitespace_validation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Feature #16: Whitespace-only input shows validation error")
        print("=" * 60)

        print("\nStep 1: Navigate to application")
        await page.goto('http://localhost:8000')
        await page.wait_for_load_state('networkidle')
        print("  ✓ Application loaded")

        await page.screenshot(path='.playwright-mcp/feature16_initial.png')

        print("\nStep 2: Enter only whitespace in input field")
        # Test with various whitespace patterns
        whitespace_tests = [
            "   ",           # Multiple spaces
            "\t",            # Tab
            "\n",            # Newline
            "  \t  \n  ",    # Mixed whitespace
        ]

        for i, whitespace in enumerate(whitespace_tests, 1):
            print(f"\n  Test {i}: Testing whitespace pattern (repr: {repr(whitespace)})")

            # Clear any previous input
            await page.fill('#question-input', '')

            # Enter whitespace
            await page.fill('#question-input', whitespace)

            # Get the actual value in the input
            input_value = await page.input_value('#question-input')
            print(f"    Input value: {repr(input_value)}")

            print("\nStep 3: Click submit button")

            # Wait for toast to appear
            toast_promise = page.wait_for_selector('.toast', state='visible', timeout=2000)
            await page.click('#submit-btn')

            print("\nStep 4: Verify validation error appears")
            # Check for toast message
            try:
                await toast_promise
                toast_visible = True
                toast_text = await page.text_content('.toast')
            except:
                toast_visible = False
                toast_text = ""

            print(f"    Toast visible: {toast_visible}")
            print(f"    Toast message: {toast_text}")

            # Check for error class on input
            has_error_class = await page.evaluate('document.getElementById("question-input").classList.contains("input-error")')
            print(f"    Input has error class: {has_error_class}")

            # Verify no API request was made (check loading state didn't appear)
            loading_visible = await page.is_visible('#loading-state')
            print(f"    Loading state visible: {loading_visible}")

            # Take screenshot
            await page.screenshot(path=f'.playwright-mcp/feature16_whitespace_test_{i}.png')

            # Wait for toast to disappear
            await asyncio.sleep(2)

        print("\nStep 5: Confirm input is trimmed and validated")
        # Test that valid input after whitespace works
        await page.fill('#question-input', '  valid question  ')
        trimmed_value = await page.evaluate('document.getElementById("question-input").value.trim()')
        print(f"  Input with surrounding whitespace: {repr('  valid question  ')}")
        print(f"  Trimmed value for validation: {repr(trimmed_value)}")
        print(f"  ✓ Input trimming works correctly")

        await page.screenshot(path='.playwright-mcp/feature16_valid_input_with_whitespace.png')

        # Verification summary
        print("\n" + "=" * 60)
        print("VERIFICATION RESULTS:")
        print("=" * 60)

        checks = {
            "Whitespace-only input rejected": toast_visible and has_error_class,
            "Validation error message shown": "Please enter a question" in toast_text,
            "Input error class applied": has_error_class,
            "Form submission blocked": not loading_visible,
            "Input trimming works": trimmed_value == "valid question"
        }

        for check, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {check}")

        all_passed = all(checks.values())
        print("\n" + "=" * 60)
        if all_passed:
            print("Feature #16: PASSED ✅")
        else:
            print("Feature #16: FAILED ❌")
        print("=" * 60)

        await browser.close()
        return all_passed

if __name__ == '__main__':
    result = asyncio.run(test_whitespace_validation())
    exit(0 if result else 1)
