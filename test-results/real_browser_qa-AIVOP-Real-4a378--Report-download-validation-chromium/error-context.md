# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: real_browser_qa.spec.ts >> AIVOP Real Browser QA Audit >> Phase 8 — Report download validation
- Location: tests\e2e\real_browser_qa.spec.ts:725:7

# Error details

```
Test timeout of 600000ms exceeded.
```

```
Error: page.waitForTimeout: Target page, context or browser has been closed
```

# Test source

```ts
  645 | 
  646 |           // Screenshot key tabs
  647 |           if (["bi", "questions", "keywords", "validation", "rec_intel", "overview", "reports"].includes(tab.key)) {
  648 |             await screenshot(page, `10_tab_${tab.key}`);
  649 |           }
  650 |         } else {
  651 |           addIssue("LOW", `Sub-tab not found in UI: ${tab.label}`,
  652 |             `Could not locate sidebar sub-item "${tab.label}"`,
  653 |             `Expand ${section.sectionLabel} → look for ${tab.label}`,
  654 |             "Verify SECTION_SUBTABS config in Sidebar.tsx");
  655 |           logFinding(`⚠️ Sub-tab not found: "${tab.label}"`);
  656 |         }
  657 |       }
  658 |     }
  659 | 
  660 |     if (tabErrors.length > 0) {
  661 |       logFinding(`❌ Tab errors: ${tabErrors.join(", ")}`);
  662 |     } else {
  663 |       logFinding("✅ All tabs navigated without crash");
  664 |     }
  665 |   });
  666 | 
  667 |   // ── Phase 7 — API Audit ────────────────────────────────────────────────────
  668 |   test("Phase 7 — API endpoint audit", async ({ request }) => {
  669 |     if (!projectId) {
  670 |       logFinding("ℹ️ No project ID — skipping deep API audit");
  671 |       return;
  672 |     }
  673 | 
  674 |     const headers = { Authorization: AUTH_HEADER };
  675 |     const endpoints = [
  676 |       `/api/v1/projects`,
  677 |       `/api/v1/projects/${projectId}`,
  678 |       `/api/v1/analysis/business-intelligence/${projectId}`,
  679 |       `/api/v1/analysis/verified-facts/${projectId}`,
  680 |       `/api/v1/analysis/questions/${projectId}?page=1&page_size=10`,
  681 |       `/api/v1/analysis/keywords/${projectId}?page=1&page_size=10`,
  682 |       `/api/v1/analysis/competitors/${projectId}`,
  683 |       `/api/v1/analysis/validation/${projectId}`,
  684 |       `/api/v1/analysis/recommendation-intelligence/${projectId}`,
  685 |       `/api/v1/analysis/analytics/${projectId}`,
  686 |       `/api/v1/analysis/historical-metrics/${projectId}`,
  687 |       `/api/v1/analysis/geo-readiness/${projectId}`,
  688 |       `/api/v1/analysis/reliability/${projectId}`,
  689 |       `/api/v1/reports?project_id=${projectId}`,
  690 |     ];
  691 | 
  692 |     for (const ep of endpoints) {
  693 |       const url = `${BACKEND_URL}${ep}`;
  694 |       const resp = await request.get(url, { headers }).catch(() => null);
  695 |       const status = resp ? resp.status() : 0;
  696 | 
  697 |       if (!resp || status === 0) {
  698 |         addIssue("HIGH", `API timeout/unreachable: ${ep}`,
  699 |           `No response from ${url}`,
  700 |           `curl -H "X-User-Id: demo_user_1" ${url}`,
  701 |           "Check backend server and endpoint registration");
  702 |         logFinding(`❌ API FAIL (no response): ${ep}`);
  703 |       } else if (status >= 500) {
  704 |         addIssue("CRITICAL", `API 5xx: ${ep}`, `${status} from ${url}`,
  705 |           `curl -H "X-User-Id: demo_user_1" ${url}`,
  706 |           "Fix backend server error for this endpoint");
  707 |         logFinding(`❌ API 5xx: ${ep} → ${status}`);
  708 |       } else if (status === 422) {
  709 |         addIssue("MEDIUM", `API 422 Unprocessable: ${ep}`,
  710 |           `${url} returned 422`,
  711 |           `curl -H "X-User-Id: demo_user_1" ${url}`,
  712 |           "Check request schema / required fields");
  713 |         logFinding(`⚠️ API 422: ${ep}`);
  714 |       } else if (status === 404) {
  715 |         logFinding(`ℹ️ API 404 (no data yet): ${ep}`);
  716 |       } else if (status === 200) {
  717 |         logFinding(`✅ API 200: ${ep}`);
  718 |       } else {
  719 |         logFinding(`ℹ️ API ${status}: ${ep}`);
  720 |       }
  721 |     }
  722 |   });
  723 | 
  724 |   // ── Phase 8 — Report Download ──────────────────────────────────────────────
  725 |   test("Phase 8 — Report download validation", async ({ page, request }) => {
  726 |     page.on("response", (resp) => {
  727 |       if (resp.url().includes("/api/") && resp.status() >= 400) {
  728 |         apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
  729 |       }
  730 |     });
  731 | 
  732 |     await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  733 |     await page.waitForTimeout(3000);
  734 |     const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
  735 |     try {
  736 |       await projItem.waitFor({ state: "visible", timeout: 15000 });
  737 |       await projItem.click();
  738 |       await page.waitForTimeout(2000);
  739 |     } catch (e) {
  740 |       logFinding("⚠️ Project item not visible for click in Phase 8");
  741 |     }
  742 | 
  743 |     // Navigate to Dashboard → Reports
  744 |     await page.locator('button.sidebar-nav-item').filter({ hasText: "Dashboard" }).click().catch(() => {});
> 745 |     await page.waitForTimeout(300);
      |                ^ Error: page.waitForTimeout: Target page, context or browser has been closed
  746 |     await page.locator('button.sidebar-sub-item').filter({ hasText: "Reports" }).click().catch(() => {});
  747 |     await page.waitForTimeout(2000);
  748 |     await screenshot(page, "11_reports_tab");
  749 | 
  750 |     // Try clicking Markdown download
  751 |     const mdBtn = page.locator('button:has-text("Markdown"), a:has-text("Markdown"), button:has-text(".md"), button:has-text("md")').first();
  752 |     if (await mdBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
  753 |       const downloadPromise = page.waitForEvent("download", { timeout: 15000 }).catch(() => null);
  754 |       await mdBtn.click();
  755 |       const download = await downloadPromise;
  756 | 
  757 |       if (download) {
  758 |         const t0 = Date.now();
  759 |         const savePath = path.join(SCREENSHOT_DIR, "report_download.md");
  760 |         await download.saveAs(savePath);
  761 |         timings["report_download_ms"] = Date.now() - t0;
  762 |         logFinding(`✅ Report downloaded in ${timings["report_download_ms"]}ms: ${download.suggestedFilename()}`);
  763 | 
  764 |         // Validate content
  765 |         const content = fs.readFileSync(savePath, "utf-8");
  766 |         const requiredSections = [
  767 |           "Business Profile", "Verified Facts", "Questions", "Keywords",
  768 |           "Competitors", "Recommendation", "GEO", "Optimization", "Reliability",
  769 |         ];
  770 | 
  771 |         for (const section of requiredSections) {
  772 |           if (!content.includes(section)) {
  773 |             addIssue("HIGH", `Missing section in report: ${section}`,
  774 |               `Report download does not contain section "${section}"`,
  775 |               "Reports tab → Download Markdown → open file",
  776 |               "Fix ReportEngineV2 to include this section");
  777 |             logFinding(`❌ Report missing section: ${section}`);
  778 |           } else {
  779 |             logFinding(`✅ Report contains: ${section}`);
  780 |           }
  781 |         }
  782 | 
  783 |         // Check table formatting
  784 |         if (!content.includes("|")) {
  785 |           addIssue("MEDIUM", "Report has no table formatting",
  786 |             "Downloaded report does not contain markdown table pipes (|)",
  787 |             "Download report → open in text editor",
  788 |             "Fix ReportEngineV2 table generation");
  789 |         } else {
  790 |           logFinding("✅ Report contains markdown tables (|)");
  791 |         }
  792 | 
  793 |         // Check for forbidden tokens in report
  794 |         for (const token of FORBIDDEN_TOKENS) {
  795 |           if (content.includes(token)) {
  796 |             addIssue("CRITICAL", `Hallucinated content in report: "${token}"`,
  797 |               `Forbidden token found in downloaded Markdown report`,
  798 |               "Download report → search for token",
  799 |               "Fix GroundingEngineV2 production gate to block hallucinated content from reports");
  800 |             logFinding(`❌ Report GROUNDING FAIL: "${token}" in downloaded report`);
  801 |           }
  802 |         }
  803 | 
  804 |         // Check for empty sections
  805 |         const emptySection = /#{1,3} .+\n\n#{1,3}/;
  806 |         if (emptySection.test(content)) {
  807 |           addIssue("MEDIUM", "Report has empty sections",
  808 |             "At least one section header is immediately followed by another header",
  809 |             "Download report → review section content",
  810 |             "Fix ReportEngineV2 to populate all sections or skip empty ones");
  811 |           logFinding("⚠️ Report may have empty sections");
  812 |         }
  813 | 
  814 |       } else {
  815 |         addIssue("HIGH", "Report download timeout",
  816 |           "Clicked Markdown button but no download event fired",
  817 |           "Reports tab → click Markdown button → wait",
  818 |           "Check ReportsTab component and download API endpoint");
  819 |         logFinding("❌ No download event received");
  820 |         await screenshot(page, "11_download_failed");
  821 |       }
  822 |     } else {
  823 |       addIssue("MEDIUM", "Markdown download button not found",
  824 |         "Cannot locate Markdown download button on Reports tab",
  825 |         "Reports tab → look for Markdown button",
  826 |         "Check ReportsTab rendering and latestReport prop");
  827 |       logFinding("⚠️ Markdown download button not found");
  828 |     }
  829 |   });
  830 | 
  831 |   // ── Phase 9 — Console Audit ────────────────────────────────────────────────
  832 |   test("Phase 9 — Console error audit", async ({ page }) => {
  833 |     const pageErrors: string[] = [];
  834 |     const warnings: string[] = [];
  835 | 
  836 |     page.on("console", (msg) => {
  837 |       if (msg.type() === "error") pageErrors.push(msg.text());
  838 |       if (msg.type() === "warning") warnings.push(msg.text());
  839 |     });
  840 |     page.on("pageerror", (err) => pageErrors.push(`pageerror: ${err.message}`));
  841 | 
  842 |     await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  843 |     await page.waitForTimeout(3000);
  844 | 
  845 |     const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
```