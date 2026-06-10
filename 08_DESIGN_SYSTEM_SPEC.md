# Design System Specification
## INT Zone Studio — Windows Desktop Application

| Field | Value |
| --- | --- |
| **Document title** | INT Zone Studio — Design System Specification |
| **Version** | 1.0 |
| **Status** | Approved for implementation |
| **Date** | 6 June 2026 |
| **Classification** | Internal / Confidential |
| **Platform** | Windows 10/11 x64 |
| **UX source of truth** | [UIUX_Specification_Desktop.md](UIUX_Specification_Desktop.md) |
| **Parent documents** | [PRD_Desktop_Application.md](PRD_Desktop_Application.md), [ARCHITECTURE_DESKTOP_APPLICATION.md](ARCHITECTURE_DESKTOP_APPLICATION.md), [04_DOMAIN_MODEL.md](04_DOMAIN_MODEL.md) |

---

## Document purpose

This specification is the **build contract** for frontend engineers implementing INT Zone Studio in React + Tailwind. It translates [UIUX_Specification_Desktop.md](UIUX_Specification_Desktop.md) §0–§6 into design tokens, component APIs, and implementation paths.

**In scope:** Tokens, typography, components, patterns, accessibility, Tailwind mapping.

**Out of scope:** Detection UI, algorithm exposure, dark theme implementation (documented for v1.1 only).

**Implementation root:** `desktop/app/src/components/`

---

## 1. Design principles

Derived from UIUX §0 — non-negotiable for all screens S01–S14.

| Principle | Build rule |
| --- | --- |
| **Quantity-surveying precision** | Always show units (m², m³, CUM). Use 2–4 dp for areas; never hide 0.207% variance. |
| **CAD-native mental model** | Layer toggles, pan/zoom, fit-to-view. No marketing card dashboards. |
| **Audit over aesthetics** | Run ID, timestamps, reviewer names visible in status bar and forms. |
| **Fail loudly** | PASS / REVIEW / FAIL / SKIP always as text + color (never color alone). |
| **Dual-monitor default** | Map uses flexible width; inspector panels fixed 320–400 px. |
| **No algorithm UI** | Frozen config read-only; no sliders for gap/threshold. |
| **Non-destructive** | Copy states "creates new file"; never "Save" on source DWG. |

---

## 2. Platform alignment

INT Zone Studio runs in **WebView2** inside Tauri. Visual language follows **Windows 11 Fluent 2** influences without requiring WinUI controls:

| Fluent concept | Web implementation |
| --- | --- |
| Segoe UI variable | `font-family: "Segoe UI Variable", "Segoe UI", system-ui` |
| Subtle elevation | `shadow-sm` + 1 px `#E0E0E0` borders |
| Focus visuals | 2 px `#0078D4` outline, 2 px offset |
| Compact density | 32 px table rows; 4 px spacing grid |
| Status semantics | Microsoft semantic colors (see §3) |

Native Windows title bar via Tauri `decorations: true`. Do not custom-draw window controls in v1.

---

## 3. Design tokens

### 3.1 Color — raw palette

| Token | Hex | Usage |
| --- | --- | --- |
| `--color-neutral-0` | `#FFFFFF` | Table row alternate |
| `--color-neutral-50` | `#FAFAFA` | Table row alternate, checklist |
| `--color-neutral-100` | `#F0F0F0` | App chrome background (UIUX §0.2) |
| `--color-neutral-200` | `#E0E0E0` | Borders, dividers |
| `--color-neutral-400` | `#A0A0A0` | Disabled text |
| `--color-neutral-600` | `#605E5C` | Secondary text, SKIP status |
| `--color-neutral-900` | `#2D2D2D` | Primary text |
| `--color-brand-primary` | `#0078D4` | Primary buttons, links, focus |
| `--color-brand-primary-hover` | `#106EBE` | Primary hover |
| `--color-status-pass` | `#107C10` | PASS |
| `--color-status-review` | `#CA5010` | REVIEW |
| `--color-status-fail` | `#D13438` | FAIL |
| `--color-status-skip` | `#605E5C` | SKIP |
| `--color-status-info` | `#0078D4` | Info toast |
| `--color-canvas-bg` | `#FFFFFF` | Drawing canvas background |
| `--color-canvas-grid` | `#EBEBEB` | Optional grid overlay |
| `--color-layer-walls` | `#605E5C` | Source walls layer |
| `--color-layer-int-boundary` | `#D13438` | INT boundaries |
| `--color-layer-int-label` | `#2D2D2D` | INT label text |
| `--color-zone-selected-fill` | `rgba(0, 120, 212, 0.15)` | Selected zone fill |
| `--color-zone-selected-stroke` | `#0078D4` | Selected zone outline |
| `--color-zone-review-stroke` | `#CA5010` | REVIEW zone outline |
| `--color-zone-fail-stroke` | `#D13438` | FAIL zone outline |

### 3.2 Color — semantic aliases

| Semantic token | Maps to |
| --- | --- |
| `--surface-canvas` | `--color-canvas-bg` |
| `--surface-chrome` | `--color-neutral-100` |
| `--surface-panel` | `--color-neutral-0` |
| `--text-primary` | `--color-neutral-900` |
| `--text-secondary` | `--color-neutral-600` |
| `--text-disabled` | `--color-neutral-400` |
| `--border-default` | `--color-neutral-200` |
| `--status-pass` | `--color-status-pass` |
| `--status-review` | `--color-status-review` |
| `--status-fail` | `--color-status-fail` |
| `--status-skip` | `--color-status-skip` |

### 3.3 Typography

| Token | Size | Weight | Line height | Use |
| --- | --- | --- | --- | --- |
| `--font-family-sans` | — | — | — | UI copy |
| `--font-family-mono` | — | — | — | INT IDs, paths, gate names |
| `--text-xs` | 11 px | 400 | 16 px | Status bar, hints |
| `--text-sm` | 12 px | 400 | 16 px | Table cells, gate detail |
| `--text-base` | 14 px | 400 | 20 px | Body, buttons |
| `--text-lg` | 16 px | 600 | 22 px | Section headers |
| `--text-xl` | 20 px | 600 | 28 px | Page titles (Home) |

**Rules:**

- Gate names: `font-mono text-sm` (e.g. `zone_count`).
- Pour No.: `font-mono text-sm` (e.g. `INT-15`).
- File paths: `font-mono text-xs truncate`.

### 3.4 Spacing and layout

Base unit: **4 px**.

| Token | Value |
| --- | --- |
| `--space-1` | 4 px |
| `--space-2` | 8 px |
| `--space-3` | 12 px |
| `--space-4` | 16 px |
| `--space-6` | 24 px |
| `--space-8` | 32 px |

| Layout region | Specification |
| --- | --- |
| App bar height | 48 px |
| Status bar height | 24 px |
| Tab bar height | 40 px |
| Table row height | 32 px (UIUX §6.1) |
| Inspector panel width | 360 px default; min 320 px, max 480 px |
| Modal max width | 560 px (blocking errors), 720 px (sign-off) |

### 3.5 Elevation and borders

| Token | Value |
| --- | --- |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.06)` |
| `--shadow-md` | `0 4px 8px rgba(0,0,0,0.08)` |
| `--radius-sm` | 4 px |
| `--radius-md` | 6 px |
| `--border-width` | 1 px |

### 3.6 Focus ring

```css
:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
```

Never remove focus outlines without replacement.

---

## 4. Tailwind implementation

**File:** `desktop/app/src/styles/tokens.css`

```css
@theme {
  --color-surface-chrome: #F0F0F0;
  --color-surface-panel: #FFFFFF;
  --color-text-primary: #2D2D2D;
  --color-status-pass: #107C10;
  --color-status-review: #CA5010;
  --color-status-fail: #D13438;
  /* ... full token set from §3 */
}
```

**Import in** `desktop/app/src/styles/globals.css`:

```css
@import "tailwindcss";
@import "./tokens.css";
```

**Utility mapping examples:**

| Design token | Tailwind class |
| --- | --- |
| PASS status text | `text-[var(--color-status-pass)]` |
| Table row | `h-8 text-sm` (32 px) |
| Primary button | `bg-[var(--color-brand-primary)] hover:bg-[var(--color-brand-primary-hover)] text-white px-4 py-2 rounded-sm` |
| Mono INT label | `font-mono text-sm` |

---

## 5. Iconography

**Library:** [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) — 20 px regular for toolbar; 16 px for inline status.

| Context | Icon | Pair with text? |
| --- | --- | --- |
| PASS | Checkmark circle | **Yes** — "PASS" |
| REVIEW | Warning | **Yes** — "REVIEW" |
| FAIL | Dismiss circle | **Yes** — "FAIL" |
| SKIP | Subtract circle | **Yes** — "SKIP" |
| Run Detection | Play | Label "Run Detection" on button |
| Export | Arrow export | Label on primary export |
| View log | Document | Link text "View log" |

**Rule:** Status icons never appear without adjacent text label (WCAG 1.4.1).

---

## 6. Component specifications

Naming: PascalCase component files under `desktop/app/src/components/{category}/`.

### 6.1 Shell components

#### AppBar

| Property | Type | Notes |
| --- | --- | --- |
| `projectName` | string | Breadcrumb segment |
| `acceptanceStatus` | AcceptanceStatus | Drives StatusBadge |
| `runEnabled` | boolean | Run button state |
| `onRun` | () => void | F5 shortcut |

**States:** Run disabled when `Running` or no project.

**Path:** `components/shell/AppBar.tsx`

#### Breadcrumb

**Anatomy:** `Home > {projectName} > {tabName?}`

**Path:** `components/shell/Breadcrumb.tsx`

#### StatusBadge (acceptance)

| Status | Background | Text |
| --- | --- | --- |
| Not Started | `neutral-200` | `neutral-900` |
| In Review | `#FDF6B2` / amber tint | `#CA5010` |
| Accepted | `#DFF6DD` | `#107C10` |
| Accepted with Conditions | `#DFF6DD` + `*` | `#107C10` |
| Rejected | `#FDE7E9` | `#D13438` |

**Path:** `components/shell/StatusBadge.tsx`

#### ProjectHeader

**Props:** `drawingFileName`, `manifestProfile`, `expectedZoneCount`, `lastRunAt`

**Path:** `components/shell/ProjectHeader.tsx`

---

### 6.2 Navigation components

#### PrimaryNav

Items: Home, Batch, Settings. Active route: 2 px bottom border `brand-primary`.

**Path:** `components/nav/PrimaryNav.tsx`

#### TabBar

Tabs: Map | Zones | Report | Exceptions | Checklist | Export

**Badge props:** `exceptionsCount`, `checklistIncomplete`

Keyboard: Ctrl+1 through Ctrl+6 (UIUX §1.6).

**Path:** `components/nav/TabBar.tsx`

#### DrawingSelector

Portfolio dropdown with sublabel `{zoneCount} zones`.

**Path:** `components/nav/DrawingSelector.tsx`

#### StepIndicator

Wizard steps: Drawing · Profile · Confirm.

**Path:** `components/nav/StepIndicator.tsx`

---

### 6.3 Action components

#### PrimaryButton

**Variants:** `primary` (default), `secondary`, `ghost`

**Primary label for run:** exactly `Run Detection` — not "Start" or "Analyze".

**Loading:** spinner replaces icon; label remains.

**Path:** `components/actions/PrimaryButton.tsx`

#### DestructiveButton

Used for Cancel run. Requires confirmation dialog copy from UIUX §5.3.

**Path:** `components/actions/DestructiveButton.tsx`

#### LinkButton

**Variant:** underline on hover; opens external/log targets.

**Path:** `components/actions/LinkButton.tsx`

---

### 6.4 Data display components

#### GateCard

```typescript
interface GateCardProps {
  name: string;           // zone_count, orphan_faces, ...
  status: 'PASS' | 'REVIEW' | 'FAIL' | 'SKIP';
  detail: string;
  onClick?: () => void;
}
```

**Layout:** Monospace name | StatusChip | truncated detail | chevron.

**Path:** `components/data/GateCard.tsx`

#### MetricTile

```typescript
interface MetricTileProps {
  label: string;
  value: string;
  unit?: string;
  sublabel?: string;
}
```

**Path:** `components/data/MetricTile.tsx`

#### StatusChip

| Status | Classes |
| --- | --- |
| PASS | `bg-green-50 text-[var(--color-status-pass)] border border-green-200` |
| REVIEW | `bg-amber-50 text-[var(--color-status-review)]` |
| FAIL | `bg-red-50 text-[var(--color-status-fail)]` |
| SKIP | `bg-neutral-100 text-[var(--color-status-skip)]` |

Always render text label inside chip.

**Path:** `components/data/StatusChip.tsx`

#### DataGrid

Generic sortable table wrapper.

```typescript
interface DataGridProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  rowHeight?: number;        // default 32
  stickyHeader?: boolean;    // default true
  selectedRowId?: string;
  onRowClick?: (row: T) => void;
  onRowDoubleClick?: (row: T) => void;
  emptyMessage?: string;
  loading?: boolean;
}
```

**States:** Loading skeleton rows; empty state message.

**Path:** `components/data/DataGrid.tsx`

Column configs live in `components/data/columns/` (T1–T7).

#### TotalsRow

Bold first column; numeric sums right-aligned.

**Path:** `components/data/TotalsRow.tsx`

#### RunHistoryTimeline

Vertical list: runId, timestamp, gate summary chips, Compare link.

**Path:** `components/data/RunHistoryTimeline.tsx`

---

### 6.5 CAD viewer components

#### DrawingCanvas

**Props:** `sceneUrl`, `selectedZoneLabel`, `visibleLayers`, `onZoneSelect`

**States:** `loading` | `ready` | `empty`

**Path:** `viewer/DrawingCanvas.tsx`

#### LayerToggleGroup

AutoCAD-style checklist with color swatch per layer.

Default layers:

| Layer ID | Label | Default visible |
| --- | --- | --- |
| `walls` | Source walls | true |
| `int_boundaries` | INT boundaries | true |
| `int_labels` | INT labels | true |
| `grid_lines` | Grid lines | false |

**Path:** `viewer/LayerToggleGroup.tsx`

#### ZoomToolbar

Buttons: Fit (F), Zoom in (+), Zoom out (−), 1:1.

**Path:** `viewer/ZoomToolbar.tsx`

#### MiniMap

160×120 px inset; viewport rectangle draggable.

**Path:** `viewer/MiniMap.tsx`

#### ZoneHighlight

| State | Stroke | Fill |
| --- | --- | --- |
| default | layer color | none |
| selected | 2 px `#0078D4` | 15% blue |
| review | 2 px `#CA5010` | none |
| fail | 2 px `#D13438` | none |

**Path:** `viewer/ZoneHighlight.tsx`

---

### 6.6 Form components

#### ManifestPicker

Radio presets: J33A, J33B, S111_A, Custom + YAML path browse.

**Path:** `components/forms/ManifestPicker.tsx`

#### PathPicker

Text input + Browse button. Validates path on blur.

**Path:** `components/forms/PathPicker.tsx`

#### DispositionRadioGroup

Options: Accept computed | Accept manifest | Reject

**Validation:** Notes required when Reject selected.

**Path:** `components/forms/DispositionRadioGroup.tsx`

#### ReviewerNameField

Defaults to Windows display name from Tauri OS API; editable.

**Path:** `components/forms/ReviewerNameField.tsx`

---

### 6.7 Feedback components

#### Toast

| Variant | Border accent |
| --- | --- |
| info | `#0078D4` |
| warning | `#CA5010` |
| error | `#D13438` |

Duration: 5 s default; pinned until dismiss for post-run "3 items need review" with link to Exceptions tab.

**Path:** `components/feedback/Toast.tsx`

#### BlockingModal

Anatomy: icon | title | cause | recommended action | primary + secondary buttons.

Template matches PRD §8.2 error message format.

**Path:** `components/feedback/BlockingModal.tsx`

#### InlineBanner

Variants: `info`, `warning`, `error`. Used top of S12 Export, S03 when InReview.

**Path:** `components/feedback/InlineBanner.tsx`

#### ProgressStageList

Stages (fixed order):

1. Loading drawing  
2. Detecting zones  
3. Building schedule  
4. Validating  

**Anatomy:** step label | icon (pending spinner check)

**Path:** `components/feedback/ProgressStageList.tsx`

---

### 6.8 Validation components

#### ChecklistRow

Columns per UIUX T5; inline Present / Area OK checkboxes; Status dropdown.

**Path:** `components/validation/ChecklistRow.tsx`

#### AdjudicationWorksheet

Fields: Zone, computed m², manifest m², Δ%, measured (optional), disposition, notes, reviewer, timestamp.

**Path:** `components/validation/AdjudicationWorksheet.tsx`

#### SignOffDispositionSelector

Options: Accepted | Accepted with Conditions | Rejected

Mirrors [08_CLIENT_SIGN_OFF_FORM.md](output/client_delivery/acceptance_review_kit/08_CLIENT_SIGN_OFF_FORM.md).

**Path:** `components/validation/SignOffDispositionSelector.tsx`

---

## 7. Table column implementations

Cross-reference UIUX §6. Implement as column definition files.

| Table | File | Screen |
| --- | --- | --- |
| T1 Zone List | `columns/zoneListColumns.ts` | S07 |
| T2 Report | `columns/reportZoneColumns.ts` | S09 |
| T3 Manifest | `columns/manifestColumns.ts` | S09 |
| T4 Exceptions | `columns/exceptionColumns.ts` | S10 |
| T5 Checklist | `columns/checklistColumns.ts` | S11 |
| T6 Batch | `columns/batchColumns.ts` | S13 |
| T7 Export manifest | `columns/exportManifestColumns.ts` | S12 |

### 7.1 Global table formatting (enforce in DataGrid)

| Rule | Implementation |
| --- | --- |
| Numeric alignment | `text-right tabular-nums` |
| INT IDs | `font-mono text-left` |
| Sticky header | `sticky top-0 bg-white z-10` |
| Alternate rows | `even:bg-neutral-50` when row count > 20 |
| Sort indicator | ChevronUp/ChevronDown 12 px in header |

### 7.2 Conditional row styling

| Condition | Style |
| --- | --- |
| face sum vs union > 2% | `bg-amber-50` (T2) |
| manifest Δ > 0.05% | `text-[var(--color-status-fail)]` (T3) |
| Union/bay coverage < 10% | `text-[var(--color-status-review)]` (T1) |
| Exception blocking | `border-l-4 border-[var(--color-status-fail)]` (T4) |

---

## 8. Screen layout patterns

### 8.1 Project hub (S03)

```
┌ AppBar ─────────────────────────────────────────┐
├ TabBar ─────────────────────────────────────────┤
├ GateCard[] (grid 4 cols) ────────────────────────┤
├ Run actions ────────────────────────────────────┤
├ Tab content (flex-1 overflow-auto) ─────────────┤
└ StatusBar ──────────────────────────────────────┘
```

### 8.2 Map + inspector (S06)

```
┌ Layer toggles | ZoomToolbar ────────────────────┐
├ Canvas (flex-1) ────────┬── Inspector 360px ────┤
│                         │  Selected zone       │
│                         │  Mini zone list      │
└ MiniMap ────────────────┴───────────────────────┘
```

**Responsive (UIUX §10):** Below 1280 px width, inspector collapses to bottom drawer.

---

## 9. Motion and animation

| Interaction | Duration | Easing |
| --- | --- | --- |
| Tab switch | 0 ms | — (instant) |
| Toast enter/exit | 200 ms | ease-out |
| Modal | 150 ms fade | ease |
| Progress spinner | continuous | — |

**`prefers-reduced-motion: reduce`:** Disable toast slide; use opacity only. Disable canvas zoom animation.

---

## 10. Theming

| Theme | v1 status |
| --- | --- |
| Light (default) | **Ship** |
| Dark | v1.1 — document tokens only, do not implement |

Dark theme token placeholders reserved in `tokens.css` under `@media (prefers-color-scheme: dark)` — commented out.

---

## 11. Accessibility checklist (per component PR)

Before merging UI components:

- [ ] Keyboard operable (Tab order logical)
- [ ] `:focus-visible` ring visible
- [ ] Status not conveyed by color alone
- [ ] Form inputs have `<label>` or `aria-label`
- [ ] Tables use `<th scope="col">`
- [ ] Modal traps focus; Esc closes (where UIUX allows)
- [ ] axe-core zero critical on story/page

---

## 12. Component inventory map

| UIUX §5 component | React path |
| --- | --- |
| AppBar | `components/shell/AppBar.tsx` |
| Breadcrumb | `components/shell/Breadcrumb.tsx` |
| StatusBadge | `components/shell/StatusBadge.tsx` |
| ProjectHeader | `components/shell/ProjectHeader.tsx` |
| PrimaryNav | `components/nav/PrimaryNav.tsx` |
| TabBar | `components/nav/TabBar.tsx` |
| DrawingSelector | `components/nav/DrawingSelector.tsx` |
| StepIndicator | `components/nav/StepIndicator.tsx` |
| PrimaryButton | `components/actions/PrimaryButton.tsx` |
| DestructiveButton | `components/actions/DestructiveButton.tsx` |
| LinkButton | `components/actions/LinkButton.tsx` |
| GateCard | `components/data/GateCard.tsx` |
| MetricTile | `components/data/MetricTile.tsx` |
| DataGrid | `components/data/DataGrid.tsx` |
| TotalsRow | `components/data/TotalsRow.tsx` |
| StatusChip | `components/data/StatusChip.tsx` |
| RunHistoryTimeline | `components/data/RunHistoryTimeline.tsx` |
| DrawingCanvas | `viewer/DrawingCanvas.tsx` |
| LayerToggleGroup | `viewer/LayerToggleGroup.tsx` |
| ZoomToolbar | `viewer/ZoomToolbar.tsx` |
| MiniMap | `viewer/MiniMap.tsx` |
| ZoneHighlight | `viewer/ZoneHighlight.tsx` |
| ManifestPicker | `components/forms/ManifestPicker.tsx` |
| PathPicker | `components/forms/PathPicker.tsx` |
| DispositionRadioGroup | `components/forms/DispositionRadioGroup.tsx` |
| ReviewerNameField | `components/forms/ReviewerNameField.tsx` |
| Toast | `components/feedback/Toast.tsx` |
| BlockingModal | `components/feedback/BlockingModal.tsx` |
| InlineBanner | `components/feedback/InlineBanner.tsx` |
| ProgressStageList | `components/feedback/ProgressStageList.tsx` |
| ChecklistRow | `components/validation/ChecklistRow.tsx` |
| AdjudicationWorksheet | `components/validation/AdjudicationWorksheet.tsx` |
| SignOffDispositionSelector | `components/validation/SignOffDispositionSelector.tsx` |

---

## 13. Storybook (recommended)

Optional but recommended from P1:

- Location: `desktop/app/src/stories/`
- One story per component with all visual states
- Visual regression via Chromatic or local screenshot diff

Minimum stories before P8: StatusChip, GateCard, DataGrid (T1 sample data), ProgressStageList.

---

## 14. Traceability

| UIUX section | This document |
| --- | --- |
| §0 Design philosophy | §1 |
| §0.2 Visual tone | §3 tokens |
| §5 Component library | §6 |
| §6 Table layouts | §7 |
| §1.6 Keyboard shortcuts | TabBar, ZoomToolbar, AppBar |
| §11 Accessibility | §11 |

| PRD FR | Design system |
| --- | --- |
| FR-14–FR-20 | §6.5 viewer |
| FR-16–FR-18 | §7 T1 |
| NFR-10 | §11 |

---

## 15. References

| Document | Use |
| --- | --- |
| [UIUX_Specification_Desktop.md](UIUX_Specification_Desktop.md) | UX source of truth |
| [04_DOMAIN_MODEL.md](04_DOMAIN_MODEL.md) | Status enums, field names |
| [06_IMPLEMENTATION_PLAN.md](06_IMPLEMENTATION_PLAN.md) | P1 design token delivery |
| [07_TEST_STRATEGY.md](07_TEST_STRATEGY.md) | axe-core gates |
| [03_Backend_Schema.md](03_Backend_Schema.md) | Engine field names for export columns |
| [ARCHITECTURE_DESKTOP_APPLICATION.md](ARCHITECTURE_DESKTOP_APPLICATION.md) | Viewer scene schema |

---

*END OF DESIGN SYSTEM SPECIFICATION*  
*INT Zone Studio — Desktop Application | v1.0 | June 2026*
