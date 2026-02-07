# Frontend Implementation Plan

## PART 1: DASHBOARD (frontend/)

### 1. BLOCKERS (Do Not Ship)
**B1. Security -- Fake Encryption with Hardcoded Keys**
- File: `frontend/src/utils/EncryptionProvider.js:15-16`
- Code:
  ```javascript
  const APP_KEY_SALT = 'codevault-encryption-salt-v1';
  const APP_IDENTIFIER = 'license-wrapper-secure-storage';
  ```
- Why: These are hardcoded constants shipped in the client bundle. Anyone with devtools can derive the exact same AES-GCM key. This isn't encryption -- it's obfuscation theater.
- Fix Plan:
  1. Remove client-side "encryption" entirely -- it provides false confidence.
  2. Use httpOnly + Secure + SameSite=Strict cookies for the auth token (server-side change required).
  3. If localStorage must be used, accept it's readable by XSS and focus on XSS prevention (CSP headers, input sanitization).

**B2. Security -- Settings Stored in Plain Text Despite Being Marked "Sensitive"**
- File: `frontend/src/utils/EncryptionProvider.js:197` marks 'codevault_settings' as a SENSITIVE_KEY.
- File: `frontend/src/contexts/SettingsContext.jsx:56,93` uses raw `localStorage.getItem/setItem('codevault_settings')`.
- Why: The settings include defaultServerUrl (line 24). If someone configured a custom API endpoint, it's in plaintext.
- Fix Plan: Either use secureLocalStorage for settings (if keeping the encryption approach), or remove codevault_settings from the SENSITIVE_KEYS array.

**B3. Security -- Hard Navigation on 401 Loses User Data**
- File: `frontend/src/services/api.js:91`
- Code: `window.location.href = '/login';`
- Why: This is a full page navigation. If a user is mid-form, their entire session state is destroyed.
- Fix Plan:
  1. Replace with an event/callback pattern: dispatch a 'session-expired' event.
  2. AuthContext listens for it, sets a sessionExpired flag.
  3. Show a modal: "Your session expired. Save your work or log in again."
  4. Use React Router's `navigate('/login')` only after user acknowledgment.

**B4. Error Handling -- logout() Not Try-Caught**
- File: `frontend/src/contexts/AuthContext.jsx:21-23`
- Why: `auth.logout()` calls `secureLocalStorage.removeItem`. If crypto context is unavailable, this throws and `setUser(null)` never executes.
- Fix Plan: Wrap in try-catch. Always call `setUser(null)` regardless of storage cleanup success.

**B5. Accessibility -- ConfirmDialog is Inaccessible**
- File: `frontend/src/components/ConfirmDialog.jsx:28-67`
- Missing: `role="alertdialog"`, `aria-labelledby`, focus trap, Escape key handler.
- Fix Plan: Mirror the pattern implemented in `Modal.jsx`.

**B6. Accessibility -- Layout Has No Skip-to-Content Link and No Nav Labeling**
- File: `frontend/src/components/Layout.jsx:59`
- Why: Sidebar `<nav>` has no `aria-label`. No skip-to-content link.
- Fix Plan:
  1. Add skip link.
  2. Add `aria-label="Main navigation"`.
  3. Add `id="main-content"`.

**B7. Build Safety -- Zero Type Checking in Production**
- File: All 64 component files are .jsx. `frontend/tsconfig.json` is strict but governs nothing.
- Fix Plan:
  1. Phase 1: Rename critical files to .tsx (contexts, services, hooks). Wire up types.
  2. Add `"build": "tsc --noEmit && vite build"` to package.json.

### 2. WARNINGS (Technical Debt)
**W1. Context Re-render Avalanche**
- Contexts: AuthContext, PricingContext, SettingsContext, BuildContext.
- Why: Value objects are created on every render.
- Fix Plan: Wrap value objects in `useMemo` and functions in `useCallback`.

**W2. God Components**
- Files: `ProjectWizard.jsx` (816 lines), `Licenses.jsx` (758 lines), `AdminDashboard.jsx` (617 lines), `Projects.jsx` (412 lines).
- Fix Plan: Extract hooks (`useProjectWizard`, `useLicenseTable`) and sub-components.

**W3. Window Event Bus Bypasses React Data Flow**
- File: `frontend/src/contexts/PricingContext.jsx:105`
- Why: Uses `window.addEventListener('user-updated')`.
- Fix Plan: Use shared callback or context coordination.

**W4. BuildContext WebSocket Has No Reconnection Logic**
- File: `frontend/src/contexts/BuildContext.jsx:192-194`
- Fix Plan: Implement exponential backoff reconnection.

**W5. consumeBuildCredit Decrements Client-Side Only**
- File: `frontend/src/contexts/PricingContext.jsx:175-182`
- Fix Plan: Make this an optimistic update with server sync.

**W6. ESLint Config Has Critical Rules Set to warn**
- Fix Plan: Change `no-undef`, `no-empty`, `no-unused-vars` to 'error'.

**W7. ProjectWizard Uses Raw fetch() Bypassing Auth**
- Fix Plan: Replace `fetch()` with `api` instance.

### 3. POLISH & NITPICKS
- P1. Login.jsx duplicate validation.
- P2. Login.jsx recreates emailRegex.
- P3. AdminDashboard.jsx redefines StatCard.
- P4. Pagination UI duplicated.
- P5. Global CSS file size.
- P6. BuildContext exposes entire map.
- P7. Background image optimization.
- P8. Mobile responsiveness for sidebar.
- P9. Missing tests.

## PART 2: LANDING PAGE (landing-page/)

### 1. BLOCKERS
**LB1. Missing Open Graph / Twitter Card Meta Tags**
- Fix Plan: Add meta tags to `index.html`.

**LB2. Accessibility -- Mobile Menu**
- Fix Plan: Add `aria-label`, `aria-expanded`, focus trap.

**LB3. Accessibility -- No prefers-reduced-motion**
- Fix Plan: Add media query to disable animations.

**LB4. Build Pipeline -- No Type Checking**
- Fix Plan: Add `"strict": true`, update build script.

### 2. WARNINGS
**LW1. Color Contrast Failures**
- Fix Plan: Update text colors.

**LW2. Empty Testimonials Section**
- Fix Plan: Populate, replace, or remove.

**LW3. APP_URL Duplicated**
- Fix Plan: Extract to `lib/config.ts`.

**LW4. Custom Tailwind Tokens Ignored**
- Fix Plan: Refactor to use semantic tokens.

**LW5. FAQ Section Not Interactive**
- Fix Plan: Use `<details><summary>` or ARIA accordion.

**LW6. JetBrains Mono Font**
- Fix Plan: Load it or remove config.

**LW7. Inter Weight 300**
- Fix Plan: Remove unused weight.

### 3. POLISH & NITPICKS
- LP1-LP8: Various HTML/CSS cleanups.

## PART 3: IMPLEMENTATION PRIORITY MATRIX

**Phase 1: Critical Security & A11y (1-2 days)**
1. Fix ConfirmDialog accessibility.
2. Wrap logout() in try-catch.
3. Replace hard navigation on 401.
4. Add skip-to-content link + aria-label.
5. Add OG/Twitter meta tags.
6. Add aria-label to mobile menu.
7. Add prefers-reduced-motion.

**Phase 2: Architecture Fixes (2-3 days)**
8. Add useMemo/useCallback to contexts.
9. Replace window event bus.
10. Add WebSocket reconnection.
11. Sync consumeBuildCredit.
12. Replace fetch() in ProjectWizard.

**Phase 3: TypeScript Migration (3-5 days)**
13. Strict tsconfig for landing page.
14. tsc in dashboard build.
15. Rename/type critical files.
16. Upgrade ESLint rules.

**Phase 4: Component Decomposition (3-5 days)**
17. Extract useProjectWizard.
18. Split Licenses.jsx.
19. Refactor AdminDashboard.
20. Extract Pagination.

**Phase 5: Polish (2-3 days)**
21. Landing page contrast.
22. Testimonials.
23. APP_URL config.
24. CSS cleanup.
25. Responsive sidebar.
26. Login validation.
