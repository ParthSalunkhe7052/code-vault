# Landing Page Overhaul: The "Zero-Lag" Cyberpunk Plan

## HR Eng
| Plan |  | A high-conversion, low-GPU overhaul based on 2025 Developer Tool trends. Focuses on "Linear-style" aesthetics, CSS-driven micro-interactions, and psychological copywriting. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick | **Status**: Research Complete | **Constraint**: Low GPU / High Zazz |

## 1. The Core Philosophy: "Static 3D"
You want "Zazz" but your laptop screams if I open a WebGL canvas.
**The Solution:** We fake it.
-   **Pre-rendered 3D Assets:** We generate high-fidelity 3D glass/neon assets using Nano Banana (Gemini).
-   **CSS Animations:** We animate the *containers* (breathing, floating, glowing borders) using CSS and `framer-motion`. This costs 0.1% of the GPU power of real 3D.
-   **The "Linear" Look:** Dark mode, 1px borders, subtle radial gradients, bento grids. This is the 2025 meta for developer tools.

## 2. Section-by-Section Implementation

### A. Hero Section: "The Vault"
*   **Headline:** "Ship Uncrackable Apps." (Big, tracked tight, gradient text).
*   **Subhead:** "The first compiler-as-a-service that turns Python & Node.js scripts into hardware-locked, native executables. No interpreters. No leaks."
*   **Visual (Right Side):**
    -   *Asset:* A **Nano Banana** generated image of a translucent, glowing "Digital Cube" floating in a void.
    -   *Animation:* CSS `float` (up/down sine wave) + `glow` (opacity pulse). Looks 3D, renders as 2D.
*   **Interactive Element (Left Side):**
    -   **The "Live" Terminal:** A code block that *types itself out* using `framer-motion`.
    -   *Content:*
        ```bash
        $ codevault build ./server.js --lock=hwid
        > Encrypting bytecode... [OK]
        > Injecting license checks... [OK]
        > Building native binary... [Done]
        > Output: ./dist/server.exe (Protected)
        ```
    -   *Why:* Developers trust CLIs. Motion grabs attention. Text rendering is cheap.

### B. Social Proof: "The Ecosystem"
*   **Strategy:** Since we lack customers, we show **Integration Compatibility**.
*   **The Bar:** "Works seamlessly with:"
    -   Monochrome logos (opacity 0.5 -> 1.0 on hover) for: Python, Node.js, Electron, Docker, GitHub Actions.
    -   *Why:* It implies authority by association.

### C. Features: "The Bento Grid"
*   **Layout:** A CSS Grid (Bento style). 2 large cards, 3 small cards.
*   **Interaction (The "Zazz"):** **Mouse-Tracking Glow Borders**.
    -   *Tech:* A small Javascript snippet that tracks mouse X/Y relative to the card and updates a CSS radial gradient background.
    -   *Effect:* As you move your mouse, the border "shines" near your cursor. Very premium, very low cost.
*   **Cards:**
    1.  **"Native Compilation"** (Large): Image of a python file transforming into a binary icon.
    2.  **"Hardware Locking"** (Small): Icon of a CPU chip with a lock overlay.
    3.  **"Offline Leases"** (Small): Icon of a severed cable with a green checkmark.

### D. "How it Works": The Pipeline
*   **Concept:** A horizontal "Assembly Line" visualization.
*   **Animation:** SVG connection lines that "flow" (dash-array animation).
*   **Steps:** `Code -> Cloud Build -> Sign -> Distribute`.
*   **Visual:** Simple, distinct SVG icons for each step.

### E. Pricing: "The Decoy"
*   **Psychology:** Highlight the "Pro" plan as the "Indie Developer" sweet spot.
*   **Visual:** The "Pro" card is scaled 1.05x larger and has a permanent border glow.

## 3. Asset Generation Plan (Nano Banana)
We need specific, consistent assets to pull this off.

1.  **Hero Image:** "Isometric 3D glass cube, glowing core, cyberpunk lighting, dark background, 8k, blender render, minimal."
2.  **Feature Icons:** "3D icon of a [CPU/Cloud/Lock], frosted glass material, neon edge lighting, dark background, isometric."
3.  **Background Texture:** "Subtle digital rain, matrix code, dark grey, low contrast, abstract data flow."

## 4. Technical Stack (Low GPU)
*   **Framework:** React + Vite (Existing).
*   **Styling:** Tailwind CSS (Existing) + **CSS Modules** (for complex glows).
*   **Motion:** `framer-motion` (Existing). Use `layout` props and `opacity/transform` only. Avoid `box-shadow` animation (expensive); use `opacity` on a pseudo-element instead.
*   **Fonts:** `Outfit` (Headings) + `JetBrains Mono` (Code).

## 5. Action Items
1.  **Generate Assets:** Create the Hero Cube and Feature Icons.
2.  **Refactor Hero:** Implement the Typewriter Terminal and Image Float.
3.  **Refactor Features:** Implement the Bento Grid with Mouse-Tracking Borders.
4.  **Polish:** Add the "Ecosystem" bar.

---
*Research synthesized. Plan upgraded. Waiting for green light to generate assets.* 🥒
