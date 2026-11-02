# Accessibility and Responsive Design Review

**Scope:** Frontend review and implementation for GitHub issue #21. This is an engineering review against WCAG 2.2 AA as a target reference; it is not a compliance certification.

## Problems identified

- The application had no skip link, several controls relied on small pointer targets, and keyboard focus was not consistently visible.
- The mobile navigation and confirmation dialog did not provide complete keyboard focus handling or focus restoration.
- The customer request form did not consistently associate required fields and validation feedback with inputs or move focus to the first invalid field.
- Loading, filtered result, and progress states lacked sufficient semantic announcements or status information.
- Data tables and the accounting chart provided limited nonvisual context; the chart's values were only available through visual bars and hover titles.
- At tablet and phone widths, the desktop navigation and multi-column areas could be difficult to use. A closed mobile drawer could remain exposed to keyboard navigation.
- Several success/demo text combinations had insufficient contrast for their small text sizes.

## Changes implemented

- Added a keyboard-visible skip link and a semantic main landmark. Main content is made inert while the mobile navigation drawer is open.
- Added visible focus styling and 44px minimum targets for primary buttons, navigation links, icon buttons, search/select controls, and key links.
- Made the mobile navigation a labeled dialog-like drawer with an accessible trigger name/state, Escape handling, a contained Tab sequence, initial focus, and focus return. The scrim is a button and is unavailable while the drawer is closed.
- Added dialog labeling and description, Escape handling, focus containment, initial focus, and focus restoration to the confirmation dialog.
- Connected request form labels, required markers, hints, and error messages using native required semantics and `aria-describedby`/`aria-invalid`. Invalid submission focuses the first invalid input; user-entered values remain available while correcting errors.
- Added live status semantics to loading and order-result feedback, improved heading structure, and exposed the orders table caption/column headers and scroll region to assistive technology.
- Converted order progress steps to a semantic ordered list and exposed progress values through labeled progress bars. The accounting chart now has a text equivalent for each displayed month and value.
- Improved small-screen navigation, spacing, card/form stacking, table scrolling, quote details, and progress-step wrapping while preserving the existing palette and layout hierarchy.
- Adjusted selected success and demo text colors to improve contrast. A browser-computed contrast spot check measured 5.39:1 for white text on the success action, 5.26:1 for the paid status, and 5.03:1 for demo notice text. These checks cover the named combinations only, not every state or rendered element.
- Added reduced-motion handling for users who request less motion.

## Files changed

- `frontend/src/App.jsx`
- `frontend/src/components/customer/RequestForm.jsx`
- `frontend/src/components/layout/CustomerHeader.jsx`
- `frontend/src/components/layout/Sidebar.jsx`
- `frontend/src/components/layout/Toast.jsx`
- `frontend/src/components/layout/Topbar.jsx`
- `frontend/src/components/orders/OrdersTable.jsx`
- `frontend/src/components/ui/ConfirmDialog.jsx`
- `frontend/src/components/ui/EmptyState.jsx`
- `frontend/src/components/ui/LoadingState.jsx`
- `frontend/src/components/ui/ProgressSteps.jsx`
- `frontend/src/components/ui/ProgressTrack.jsx`
- `frontend/src/pages/AccountingPage.jsx`
- `frontend/src/pages/OrdersPage.jsx`
- `frontend/src/pages/ReceiptsPage.jsx`
- `frontend/src/pages/customer/OrderTrackingPage.jsx`
- `frontend/src/styles/app.css`

## Responsive and browser checks

Playwright browser automation was available against the local Vite development server. No other browser or assistive technology was used.

- Dashboard, Orders, Quotes, Receipts, Accounting, customer request, quote review, tracking, and order detail routes were checked at **375, 390, 430, 768, 1024, 1280, and 1440px**; no page-level horizontal overflow was found. Wide order tables remain in their labeled horizontal scroll region.
- At 375px, checked that the mobile menu opens, announces expanded state, receives initial focus, closes on Escape, and restores focus to the trigger. Tab and Shift+Tab wrapped within the open drawer.
- Checked empty customer request submission: focus moved to the first invalid field, required field errors were visible and associated, and the form retained entered values through validation. Submitted test-only demo data to exercise the quote review view; removed the demo local-storage record after testing. No real customer/payment data or payment flow was used.
- Checked confirmation dialog labeling and keyboard focus containment; Escape closed it and returned focus to the opener.
- Checked the browser accessibility snapshot for primary landmarks and navigation structure. This is not a screen-reader test.
- Checked browser console output: **0 errors and 0 warnings** were reported.

## Validation commands

- `npm run lint` — passed.
- `npm run build` — passed; Vite produced the production bundle.
- `npm run` — confirmed the project defines `dev`, `build`, `lint`, and `preview` scripts only. There is no automated frontend test script or existing frontend test suite to run.

## Remaining limitations and follow-up

- A manual screen-reader run, full keyboard walkthrough of every route, zoom/reflow check at 200% and 400%, and exhaustive contrast review of all text, icons, disabled, hover, focus, and status combinations were not performed.
- Checkout is demo-only. No live payment or backend checkout behavior was tested or changed.
- Loading and error semantics were reviewed in the implementation; a deterministic network failure/loading browser scenario was not available in the local demo. Confirm announcements and recovery paths again when real API integration is available.
- Tiny legacy typography remains in parts of the established design. Contrast and readability across all browser zoom and text-resize combinations need further manual validation.
- No independent automated accessibility scanner was run. The browser checks and contrast spot checks do not establish WCAG conformance.
