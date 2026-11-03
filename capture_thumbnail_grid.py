import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 1200 x 800 (exact 3:2 Devpost thumbnail ratio)
        page = await browser.new_page(viewport={"width": 1200, "height": 800})
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        tag_btn = page.locator(".query-tag-btn").first
        await tag_btn.click()

        await page.wait_for_selector(".ag-row", timeout=15000)
        await asyncio.sleep(4.5)

        # Clear toasts
        await page.evaluate("""() => {
            const toasts = document.querySelectorAll('.toast, .notification, [class*="toast"]');
            toasts.forEach(el => el.remove());
        }""")

        # Scroll to view AG Grid Cockpit table
        await page.evaluate("window.scrollTo(0, 1050)")
        await asyncio.sleep(0.5)

        thumb_path = "C:/Users/yuvan/.gemini/antigravity/scratch/ProductFind/devpost_thumbnail_grid.png"
        brain_path = "C:/Users/yuvan/.gemini/antigravity/brain/143f81a9-601b-41b7-ae02-27658d88dd44/devpost_thumbnail_grid.png"
        await page.screenshot(path=thumb_path)
        await page.screenshot(path=brain_path)
        await browser.close()
        print("Success: Captured AG Grid 3:2 thumbnail!")

if __name__ == "__main__":
    asyncio.run(main())
