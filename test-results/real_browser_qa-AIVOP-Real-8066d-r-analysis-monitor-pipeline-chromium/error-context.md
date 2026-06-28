# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: real_browser_qa.spec.ts >> AIVOP Real Browser QA Audit >> Phase 2 — Trigger analysis & monitor pipeline
- Location: tests\e2e\real_browser_qa.spec.ts:165:7

# Error details

```
Test timeout of 600000ms exceeded.
```

```
Tearing down "context" exceeded the test timeout of 600000ms.
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - complementary [ref=e3]:
      - generic [ref=e4]:
        - generic [ref=e5]:
          - img [ref=e6]
          - generic [ref=e8]: GeoPilot
        - button "Toggle theme" [ref=e9] [cursor=pointer]:
          - img [ref=e10]
      - button "Search... ⌘K" [ref=e13] [cursor=pointer]:
        - img [ref=e14]
        - generic [ref=e17]: Search...
        - generic [ref=e18]: ⌘K
      - generic [ref=e19]:
        - generic [ref=e20]: Workspace
        - combobox [ref=e21] [cursor=pointer]:
          - option "Preetham (User 1)" [selected]
          - option "David Miller (User 2)"
          - option "Sarah Connor (User 3)"
      - navigation [ref=e22]:
        - generic [ref=e23]: Navigation
        - button "Overview" [ref=e24] [cursor=pointer]:
          - img [ref=e26]
          - generic [ref=e31]: Overview
        - button "Search & Keywords" [ref=e32] [cursor=pointer]:
          - img [ref=e34]
          - generic [ref=e37]: Search & Keywords
        - button "Competitor Intelligence" [ref=e38] [cursor=pointer]:
          - img [ref=e40]
          - generic [ref=e41]: Competitor Intelligence
        - button "AI Visibility" [ref=e42] [cursor=pointer]:
          - img [ref=e44]
          - generic [ref=e47]: AI Visibility
        - button "Content Optimizer" [ref=e48] [cursor=pointer]:
          - img [ref=e50]
          - generic [ref=e53]: Content Optimizer
        - button "Execution & Health" [ref=e54] [cursor=pointer]:
          - img [ref=e56]
          - generic [ref=e58]: Execution & Health
      - generic [ref=e59]:
        - generic [ref=e60]:
          - generic [ref=e61]: Projects (4)
          - button "Create new project" [ref=e62] [cursor=pointer]: +
        - list [ref=e63]:
          - listitem [ref=e64]:
            - button "The Library Company Delete The Library Company" [ref=e65] [cursor=pointer]:
              - generic [ref=e66]: The Library Company
              - button "Delete The Library Company" [ref=e67]: ×
          - listitem [ref=e68]:
            - button "Empty Library Company Delete Empty Library Company" [ref=e69] [cursor=pointer]:
              - generic [ref=e70]: Empty Library Company
              - button "Delete Empty Library Company" [ref=e71]: ×
          - listitem [ref=e72]:
            - button "TheLibraryCompany_QA_1782567312116 Delete TheLibraryCompany_QA_1782567312116" [ref=e73] [cursor=pointer]:
              - generic [ref=e74]: TheLibraryCompany_QA_1782567312116
              - button "Delete TheLibraryCompany_QA_1782567312116" [ref=e75]: ×
          - listitem [ref=e76]:
            - button "preetham Delete preetham" [ref=e77] [cursor=pointer]:
              - generic [ref=e78]: preetham
              - button "Delete preetham" [ref=e79]: ×
    - main [ref=e80]:
      - generic [ref=e81]:
        - generic [ref=e82]:
          - generic [ref=e83]:
            - heading "TheLibraryCompany_QA_1782567312116" [level=1] [ref=e84]
            - link "https://www.thelibrarycompany.com" [ref=e86] [cursor=pointer]:
              - /url: https://www.thelibrarycompany.com
          - button "crawling..." [disabled] [ref=e87]: crawling...
        - generic [ref=e90]:
          - generic [ref=e91]:
            - generic [ref=e92]: Pipeline Executing
            - generic [ref=e93]: "Stage: crawling · Agent: Crawler"
          - generic [ref=e94]:
            - generic [ref=e95]:
              - generic [ref=e96]: 1181s
              - text: elapsed
            - generic [ref=e97]: "ETA: 120s"
        - generic [ref=e100]:
          - generic [ref=e101]:
            - generic [ref=e102]:
              - heading "Executive Overview" [level=2] [ref=e104]
              - paragraph [ref=e105]: AI Visibility intelligence summary for this project
            - button "Run Analysis" [ref=e107] [cursor=pointer]:
              - img [ref=e108]
              - text: Run Analysis
          - status [ref=e110]:
            - img [ref=e112]
            - generic [ref=e114]: No intelligence generated yet
            - paragraph [ref=e115]: Run your first analysis to populate the executive dashboard with GEO scores, recommendations, and competitor insights.
            - button "Run Initial Analysis" [ref=e117] [cursor=pointer]
  - generic "Notifications"
  - alert [ref=e118]
```