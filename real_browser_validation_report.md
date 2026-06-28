# AIVOP Real Browser Validation Report

**Generated**: 2026-06-27T14:40:46.729Z  
**Target**: https://www.thelibrarycompany.com  
**Frontend**: http://localhost:3000  
**Backend**: http://localhost:8000  
**Project Created**: TheLibraryCompany_QA_1782571218988  

---

## Executive Summary

| Status | Critical | High | Medium | Low | Total Issues |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **🟡 PARTIAL PASS** | 0 | 0 | 0 | 0 | 0 |

---

## Grounding Audit

Forbidden tokens checked (MUST NOT appear in any UI or API response):
- `Benjamin Franklin`
- `Philadelphia`
- `1731`
- `Historical Research Library`
- `Library Company of Philadelphia`
- `librarycompany.org`

✅ **No grounding failures detected.**

---

## Question Audit

_None_


---

## Keyword Audit

_None_


---

## API Audit

### Failed Endpoints (4xx / 5xx)

✅ No API failures detected during browser session.


---

## UI Audit

| Tab | Status |
| :--- | :--- |


---

## Performance Audit

| Metric | Value |
| :--- | :--- |
| Initial Load (wall clock) | 3555ms |
| Backend Health Check | N/Ams |
| Analysis Trigger | N/Ams |
| Analysis Total Time | N/A |
| Questions Tab Load | N/Ams |
| Keywords Tab Load | N/Ams |
| Report Download | N/Ams |

---

## Console Errors

✅ No console errors detected.


---

## Screenshots

All screenshots saved to: `tests/e2e/qa_screenshots/`

| File | Description |
| :--- | :--- |
| 01_landing.png | Landing page / Create Project form |
| 02_form_filled.png | Form filled with target URL |
| 03_project_dashboard.png | Project dashboard after creation |
| 04_project_loaded.png | Project header loaded |
| 05_pipeline_running.png | Pipeline banner visible |
| 06_pipeline_completed.png | Pipeline completion card |
| 07_business_intelligence.png | Business Intelligence tab |
| 08_questions_tab.png | Questions tab |
| 09_keywords_tab.png | Keywords tab |
| 10_tab_*.png | Individual tab screenshots |
| 11_reports_tab.png | Reports tab |
| 12_nextjs_error_dialog.png | Error dialog (if present) |
| 13_final_state.png | Final app state |

---

## Critical Issues

_None_


---

## High Issues

_None_


---

## Medium Issues

_None_


---

## Low Issues

_None_


---

## All Findings Log

```
⚠️ Project item not visible for click in Phase 9
Console errors on clean load: 0
Console warnings on clean load: 0
✅ No Next.js error dialog visible
Total console errors across all phases: 0
Performance metrics:
  TTFB: 74ms
  DOMContentLoaded: 528ms
  Load event: 896ms
  Initial load (wall): 3555ms
Screenshot: 13_final_state.png
```
