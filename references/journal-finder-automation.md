# Journal Finder Playwright Automation Notes

Detailed implementation notes for each publisher's Journal Finder. Each pattern was verified working.

## Common Playwright Setup

All publishers use headless Chromium via `playwright.async_api.async_playwright`. Anti-detection baseline:

```python
browser = await p.chromium.launch(
    headless=True,
    args=['--disable-blink-features=AutomationControlled']
)
context = await browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...',
)
await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
```

## Cookie Consent Pattern

Generic handler for most publishers:

```python
consent_selectors = [
    'button:has-text("Accept")',
    'button:has-text("Accept all")',
    'button:has-text("Accept cookies")',
    '#onetrust-accept-btn-handler',
]
for selector in consent_selectors:
    button = await page.query_selector(selector)
    if button and await button.is_visible():
        await button.click()
        await page.wait_for_timeout(1000)
        return
```

**WOS exception**: OneTrust overlay blocks all interactions. Must remove DOM elements entirely:
```python
await page.evaluate('''() => {
    document.querySelectorAll('[id*="onetrust"], [class*="onetrust"]').forEach(el => el.remove());
    const sdk = document.querySelector('#onetrust-consent-sdk');
    if (sdk) sdk.remove();
}''')
```

---

## 1. Elsevier Journal Finder

**URL**: `https://journalfinder.elsevier.com/`
**Input**: Single textarea (find by tag)
**Submit**: `button[type="submit"]` or `button:has-text("Find journals")`
**Wait**: 10s after click
**Extraction**: Lines immediately before `"Save journal"` are journal names.
**Typical yield**: 40 journals, extract top 10.

## 2. Taylor & Francis Journal Suggester

**URL**: `https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-suggester/`
**Input**: `textarea[placeholder*="abstract"]` — fill with abstract
**Submit**: `button:has-text("Reveal suggested journals")`
**Wait**: 15s (slow AI processing)
**Extraction**: Two-column card layout in "Suggested Journals" section. Skip `aboutmetrics`, `learn more`, `publishes`, `open select`, `an open access journal`.
**Typical yield**: 10 journals (5 rows × 2 columns).
**Note**: Must dispatch `input` event after filling.

## 3. Wiley Journal Finder

**URL**: `https://www.wiley.com/en-ie/journal-finder/abstract/?type=match`
**⚠️ CRITICAL: Two required fields** — `textarea[name="term"]` (title) AND `textarea[name="abstract"]`. Both must be filled with `input` events dispatched. Button `is_enabled()` only after both have content.
**Submit**: `button:has-text("FIND JOURNALS")` — wait for `is_enabled()` loop.
**Wait**: 15s after click
**Extraction**: After `"Showing X journals"`, names appear after `"OFFERS OPEN ACCESS"` or `"FULLY OPEN ACCESS"` lines. Skip `days`, `submission to`, `acceptance rate`, `article publication`, `journal impact factor`.
**Anti-bot**: Requires `--disable-blink-features=AutomationControlled` + custom user-agent. Cloudflare blocks otherwise.
**Typical yield**: 5-8 journals per page.

## 4. Springer Journal Finder

**URL**: `https://link.springer.com/journals`
**Input**: `#manuscript-abstract` (input, not textarea)
**Submit**: `button:has-text("Find journals")`
**Wait**: `networkidle` for page load, 15s after click
**Extraction**: After `"Showing"`, each card starts with journal name, next line is `"Publishing Model"`. Subject-area tags follow — filter with stoplist: `environmental sciences`, `ecology`, `atmospheric science`, `earth sciences`, `climate sciences`, `biology`, `chemistry`, `geography`, etc.
**Typical yield**: 20 journals. Occasional `ERR_CONNECTION_CLOSED` — retry works.

## 5. Web of Science (Clarivate)

**URL**: `https://mjl.clarivate.com/home`
**⚠️ No login required for search.** Login button visible but search works without it.
**Input**: `input[placeholder*="Search Journal"]` — fill with keywords
**Submit**: `await input.press('Enter')` (button may be obscured by cookie overlay)
**Cookie**: Must remove OneTrust DOM elements entirely (see above).
**Wait**: 10s after Enter
**Extraction**: After `"Journals Relevant To"`, journal names are ALL CAPS lines (10-100 chars) followed by `"Publisher:"` on next line. Filter out publisher addresses (`street`, `avenue`, `ltd`, `inc`, `gmbh`).
**Typical yield**: 10+ journals (184 total, paginated). Convert to title case: `line.title()`.

---

## Match Score Formula

`match_score = max(0.1, 1.0 - (rank - 1) * 0.05)` → 1→1.00, 2→0.95, ..., 10→0.55
