# Journal Finder API Analysis Notes

## Target Websites

| Publisher | URL | Input Required | Auth | Status |
|---|---|---|---|---|
| Elsevier | https://journalfinder.elsevier.com/ | Title + Abstract (single field) | No | ✅ Working |
| Wiley | https://www.wiley.com/en-ie/journal-finder/abstract/?type=match | Title + Abstract (separate fields) | No | ✅ Working |
| Taylor & Francis | https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-suggester/ | Abstract (single field) | No | ✅ Working |
| Springer | https://link.springer.com/journals | Title + Abstract (single field) | No | ✅ Working |
| Web of Science | https://mjl.clarivate.com/home | Keywords (single field) | **No login required for search** | ✅ Working |

## Key Finding: WOS Does NOT Require Login

Confirmed with fresh browser context (no cookies, no login state):
- Login button is visible but search works without authentication
- "Search Journals" feature is fully functional
- "Match Manuscript" feature may require login (not tested)
- Cookie overlay must be removed via DOM manipulation before interacting

## Analysis Approach

All sites are JavaScript-rendered. Use Playwright (not simple HTTP fetch) for all publishers.

Detailed Playwright patterns: see `references/journal-finder-automation.md`
