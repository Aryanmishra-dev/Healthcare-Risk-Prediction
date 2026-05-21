import asyncio
from playwright.async_api import async_playwright

async def run_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err}"))
        page.on("console", lambda msg: errors.append(f"Console {msg.type}: {msg.text}") if msg.type == 'error' else None)
        
        print("1. Loading homepage...")
        await page.route("**/*", lambda route: route.continue_() if "127.0.0.1" in route.request.url or "localhost" in route.request.url or "unpkg.com" in route.request.url else route.abort())
        await page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
        await page.wait_for_selector("#nav-home")
        
        print("2. Testing navigation...")
        # Click Diabetes
        await page.click("#nav-diabetes")
        await asyncio.sleep(0.5)
        is_diabetes_active = await page.evaluate("document.getElementById('section-diabetes').classList.contains('active')")
        print(f"   Diabetes tab active: {is_diabetes_active}")
        
        # Click Heart
        await page.click("#nav-heart")
        await asyncio.sleep(0.5)
        is_heart_active = await page.evaluate("document.getElementById('section-heart').classList.contains('active')")
        print(f"   Heart tab active: {is_heart_active}")
        
        # Click Lung
        await page.click("#nav-lung")
        await asyncio.sleep(0.5)
        is_lung_active = await page.evaluate("document.getElementById('section-lung').classList.contains('active')")
        print(f"   Lung tab active: {is_lung_active}")
        
        print("3. Testing Diabetes Prediction Form...")
        await page.click("#nav-diabetes")
        await asyncio.sleep(0.5)
        
        # Click Generate Prediction
        await page.click("button[aria-label='Generate AI Prediction for Diabetes']")
        
        print("   Waiting for HTMX response...")
        try:
            # Wait for the result to populate
            await page.wait_for_selector("#diabetes-result .doctor-widget", timeout=5000)
            print("   Prediction generated successfully!")
            
            result_text = await page.locator("#diabetes-result h3").first.text_content()
            print(f"   Result title: {result_text}")
        except Exception as e:
            print(f"   Failed to get prediction: {e}")
        
        print("\n--- Console Errors Captured ---")
        if not errors:
            print("No console errors detected!")
        else:
            for err in set(errors):
                print(err)
                
        await browser.close()

asyncio.run(run_tests())
