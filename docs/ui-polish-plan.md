# Scientific workspace UI polish — draft plan

Status: review and planning only. No implementation authorized for this phase yet.

## Scope and evidence

Extend the approved Initial page / My Structures design to Scattering Geometry
and Structure Factors, including their six subtabs. Keep this a presentation task:
layout, spacing, visual hierarchy, labels, focus states, and plot legibility.
Preserve the domain calculations, controller contracts, numeric precision, import
lifecycle, automatic-update behavior, result selection semantics, and export data.

Reviewed the current widget code and actual offscreen Qt renders, before and after
calculations, using the bundled idealized rock-salt example at 8 keV and an isolated
temporary library. No real library records were edited. Inspected all six subtabs
at 1440 × 900 and attempted 1100 × 700. The current scientific workspace forces
the latter to approximately 1301 × 702 in this environment. Native macOS chrome
and scaling will need a final check during implementation.

## Shared design direction

- Reuse the approved restrained blue, pale blue, white, and soft gray palette.
- Use pale blue to identify the starting input area; solid blue marks the main
  calculation action. Selection uses pale blue with a clear border or indicator.
- Keep History, Export, Details, and management actions secondary. Do not make
  the selected plane or fixed-angle toggle resemble a success notification.
- Distinguish editable fields from read-only outputs without making outputs look
  disabled. Keep results readable and copyable.
- Use consistent panel padding, heading weights, field heights, and numeric
  alignment. Stop stretching small input forms to fill available vertical space.
- Keep scientific plot surfaces white. Preserve beam/vector meanings, color-map
  semantics, reciprocal-space units, and the distinction between |F| and intensity.
- Treat these as repeated exploration workflows rather than numbered wizards.
  Use clear section headings and a predictable input → action → result order.

## Proposed changes by area

### Navigation and experiment context

Observed: the large image-based feature buttons and the 200-pixel Scattering
Geometry parameter sidebar consume substantial width. Some subtab titles clip.

Proposal:

- Keep both navigation levels, but make feature selection and the active subtab
  more obvious using the same selected-state style as My Structures.
- Retain the feature icons initially; tighten their surrounding space and make
  labels legible. Replacing those icons is not assumed to be approved.
- Shorten overly long subtab labels without losing meaning. Candidate labels:
  “Angles → HKL”, “HKL → Angles”, “Plane → Angles”, “HKL Scan”; show “Fixed 2θ”
  inside the latter two pages. Use “2θ” consistently as a display label only.
- Recommended, pending user preference: replace the full Scattering Geometry
  parameter sidebar with a compact crystal/beam context strip and a Details
  action. Keep complete parameters reachable. Preserve per-subtab energy inputs
  in Structure Factors; a global beam readout must not imply it is the energy
  used for a locally calculated structure-factor plot.

### Scattering Geometry — Angles → HKL

Observed: the result fields resemble inputs; the two plots have no surrounding
titles; the atomic plot and labels can clip. Much of the left column is empty.

Proposal:

- One compact Scattering angles input panel with a solid-blue Calculate HKL action.
- A clearly separate HKL result area with quieter read-only surfaces and aligned
  H, K, L values. Preserve current precision and copy behavior.
- Indicate that values update as angles are edited, because that behavior already
  exists. Do not change the automatic calculation or remove its explicit button.
- Label and consistently frame Geometry and Atomic structure previews; fit their
  legends and labels, and give the atomic preview an honest empty state.

### Scattering Geometry — HKL → Angles

- Group the target H, K, L values and fixed-angle constraint into a compact input
  area, with an obvious order and a single primary Calculate angles button.
- Style Fix χ / Fix φ as a joined selection control; make the active fixed value
  visibly associated with the selection.
- Give the solution table a clear header/count, aligned numeric columns, and a
  compact History action. Avoid the current full-width History button competing
  with Calculate.
- Separate selection from feasibility. Prefer quiet row backgrounds with an
  explicit feasibility label/indicator based on the existing result flag rather
  than relying on solid pink/green rows alone. Do not alter the feasibility rule.

### Scattering Geometry — Plane → Angles, fixed 2θ

- Follow the same layout and result styling as HKL → Angles.
- Place HK / HL / KL selection next to the corresponding two index inputs.
- Group fixed 2θ and fixed χ/φ coherently, with consistent labels and alignment.
- Preserve which component is solved and all existing values and control behavior.

### Scattering Geometry — HKL Scan, fixed 2θ

Observed: a small Fixed Angles form stretches into a very tall panel; the result
table dominates through pink fills; table and plot compete for vertical space.

- Top-align a compact input column: fixed angles, plane, index ranges, point count,
  then a primary “Calculate scan” action.
- Give results a small toolbar with a result count and the existing Export CSV
  action; retain numeric columns, scrolling, sorting, and data precision.
- Keep the table and trajectory plot together. Recommended: a vertical splitter
  so the user can adjust their relative space without changing either workflow.
- Use subtle group separators and explicit feasibility information instead of a
  large uniform red/pink surface. Keep explanatory notes brief and close to the
  information they explain.

### Structure Factors — HKL plane

Observed: the starting controls are below the 3D plot, the bright green plane
selector dominates the calculation button, and the fixed-index slider sits in
an unnecessarily tall panel separate from the plane choice.

- Move a compact control area above the plots: energy, HK/HL/KL selection, a
  primary “Calculate structure factors” action, and secondary Export.
- The existing “Initialize Calculator” action already calculates and draws plots;
  rename the button without changing its signal or calculation sequence.
- Associate the selected plane and fixed-index slider clearly with the 2D view.
- Recommended, pending user preference: keep 3D overview and 2D plane together,
  with more space for 2D. Do not remove the 3D view without agreement.
- Replace the prominent green “initialized successfully” sentence with a quiet
  status line. Any displayed calculation context must come from the actual
  rendered result/snapshot, not merely the current editable energy field.

### Structure Factors — Customized plane

Observed: four nearly equal quadrants compete, U/V/Center fields are scattered,
and the relationship between calculating structure factors and accessibility is
not visually clear.

- Put energy and plane definition together: U, V, Center in an aligned row/grid,
  followed by U/V ranges and the calculation/export actions.
- Keep the current vector format and parsing behavior. Clarify labels and input
  examples without introducing a new editor or changing validation rules.
- Give accessibility constraints their own compact secondary section: fixed
  angle selection, consistent min/max columns, and Check accessibility.
- Preserve the current automatic accessibility check after calculation. Explain
  the red × overlay with a small legend; do not change its classification.
- Give the 2D plane visual priority if approved, and keep the 3D plane overview
  legible alongside it. Adjust label spacing, axes margins, and legend placement.
- Preserve the current minimal |F| reflection hover information. Do not add more
  scientific metrics or modify filtering/structure-factor/export calculations.

## Separate UI correctness items found during review

These presentation defects were corrected within the UI implementation; their
underlying calculation and export handlers remain unchanged.

1. HKL Scan labels columns 5/6 as φ/χ but populates them with χ/φ respectively.
   Align headers and displayed values; verify CSV column meanings separately.
   Evidence: `hkl_scan_components.py`, header at line 372 and population at
   lines 448–449 in the reviewed checkout.
2. HKL Scan constructs an Export CSV button in a wrapper layout, but the parent
   subtab adds only the table widget. The button is absent from the rendered tab.
   Expose that existing action in the results toolbar; retain its export handler.

Do not silently extend this design task into a numerical or coordinator refactor.
Any other behavioral issues discovered during implementation should be reported
separately before expanding scope.

## Accepted interview decisions

1. Emphasize numerical results in Scattering Geometry.
2. Panel rearrangement is allowed.
3. Defer Reflection List & Export popup polishing.
4. Retain feature navigation on the left and the information panel on the right,
   per the user's follow-up. Keep the information panel compact and avoid adding
   vertical header rows.
5. Prioritize 2D and make 3D secondary; unify styling within each feature.

Implementation boundaries: preserve feature icons, keep existing calculations
and automatic updates, keep History dialogs functionally unchanged, and make no
new scientific controls.

## Implementation sequence after approval

1. Finalize layout choices from the interview. Refine one representative
   Scattering Geometry view and the HKL-plane view as the visual references.
2. Apply scoped presentation styles to navigation, fields, buttons, panel headings,
   selections, and result tables. Avoid a global stylesheet override.
3. Implement the Scattering Geometry layouts across its four subtabs, including
   compact context and scan table/plot arrangement if approved.
4. Implement both Structure Factors layouts, keeping plot semantics and existing
   update paths intact. Include the export popup only if explicitly selected.
5. Fit actual Qt layouts and Matplotlib canvases at normal/compact sizes and 2×
   scaling; inspect all key states and exercise only relevant regression tests.
6. Deliver before/after screenshots and a concise change/verification summary.

Likely implementation files are the two feature tab views, their UI component
files, scoped QSS, and (only as needed) shared visualizer presentation code and
main-window navigation/sizing. Domain modules are outside scope. Controller
changes are not planned; propose any necessary exception before making it.

## Acceptance criteria

- The starting controls and primary action are recognizable on every subtab.
- Editable inputs, computed results, selected options, and feasibility are visually
  distinct; meaning does not rely on color alone.
- Subtab names, primary controls, numeric results, plot axes, and legends do not
  clip at the agreed sizes. Aim for an approximately 1100 × 700 application window
  without shrinking readable text; report a genuine limit rather than forcing a
  larger minimum to hide a layout problem.
- Check empty/calculated/no-solution/multiple-solution/geometry-only states, all
  HK/HL/KL modes, both fixed-angle modes, scan scrolling, and long crystal names.
- Preserve numeric values, precision, units, solution mapping, automatic update
  timing, accepted-structure state, and reflection snapshot/export provenance.
- Verify mouse/keyboard selection, focus, copy, existing History and Export actions,
  and resizing. Use isolated test data; do not modify the user's saved library.

Implementation was authorized by the user's “now go” instruction. The resulting
UI uses left-hand feature navigation, a compact right-hand information panel, pinned
conversion results with scrollable inputs, and 2D-first Structure Factor views.
The scan table's χ/φ headings now match their values and its existing CSV action
is visible. Feasibility uses explicit text with restrained color. Backend and
controller code and the deferred reflection popup are unchanged.

## Verification

Latest refinement: use `tth` throughout UI labels and tab names. The HKL Scan
table spans the working area below the controls and plot; the vertical splitter
allows users to adjust its height. The right information panel is 165 px wide
with a neutral background and subdued headings. Re-rendered normal and compact
layouts and passed 30 relevant workspace/scattering UI tests after this change.

- 87 focused tests passed: feature UI wiring, reflection popup/export regression
  tests, setup preservation, 2D visualizers, and compact workspace/scan CSV checks.
- Rendered all six subtabs at 1440 × 900 and 1100 × 700 with isolated example
  data, including a 2× scale render pass. Compact windows remain 1100 × 700;
  longer inputs scroll vertically while conversion results and Calculate stay visible.
- Inspected secondary atomic/3D views separately. These are offscreen Qt checks,
  not a manual interaction session in the user's running app.
- Existing Matplotlib ellipse styling and hidden-canvas tight-layout warnings
  remain; no domain or controller files were changed.
