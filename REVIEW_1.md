# Review of REQUIREMENT_1 implementation

Reviewed on 2026-09-04 against the current working tree and baseline commit `c28d36e`.

**Verdict: changes required before treating REQUIREMENT_1 as complete or starting REQUIREMENT_2.** The architecture is a useful improvement, but the normal Customized Plane workflow is broken, validation still permits incorrect scientific interpretation, and several lifecycle guarantees in `IMPLEMENTATION_LOG.md` are not met.

This was a review only. Application code, tests, and architecture rules were not changed.

## Critical — fix before proceeding

### 1. [P1] Customized Plane retains the discarded calculator after the first import

Location: [StructureFactorController.invalidate_structure](/Users/hongxunyang/workplace/tools/advisor/advisor/features/structure_factor/controllers/structure_factor_controller.py:62), with the child binding in [StructureFactorTab](/Users/hongxunyang/workplace/tools/advisor/advisor/features/structure_factor/ui/structure_factor_tab.py:152).

Invalidation creates a new calculator and assigns it to the controller and parent tab. `CustomizedPlaneWidget.calculator` still points to the previous instance; its `set_calculator()` is called only when the widget is constructed.

**Reproduced:** create a real `AppController`, import `tests/fixtures/cif/high_precision.cif`, run setup Initialize, then initialize Customized Plane. The parent calculator becomes initialized, but the child calculator is a different, uninitialized object. `update_plots()` returns before calculating reflections, and the child snapshot remains `None`, despite the success status. This happens on the first normal CIF import, not only on replacement.

**Required correction:** provide one narrow view method that rebinds every dependent child when the controller replaces its calculator, or adopt an equally explicit reset contract. Keep calculator ownership inside the feature. Test actual calculation and a populated snapshot after first import, A → B, and Reset → import; also verify that the snapshot belongs to the current CIF and energy.

### 2. [P1] Required atom tags are mistaken for usable atomic data

Location: [cif_adapter.py](/Users/hongxunyang/workplace/tools/advisor/advisor/domain/cif_import/cif_adapter.py:133).

`fc.cif_check()` checks required keys and missing-value markers; it does not establish a nonempty, valid atom table or a supported numerical interpretation. Checking raw keys is necessary to avoid backend defaults, but it is not sufficient validation.

**Reproduced using the high-precision fixture:**

- Change `Si2 0.25 0.25 0.25` to `Si2 . 0.25 0.25`. Import returns `ready` and “Ready for geometry and structure factors.” The installed backend silently converts the missing x coordinate to `0.0` and calculates a finite F(100), approximately `25.10792627 + 0.42711771j`, from that invented coordinate.
- Remove both atom rows while retaining the loop's four column tags. Import still returns `ready`; subsequent structure-factor calculation fails with `number sections must be larger than 0.`

**Required correction:** validate nonempty, consistent atom rows, required numeric values, and supported species/atomic interpretation before advertising structure-factor capability. Explicitly handle both `.` and `?`; do not rely on the backend's permissive numeric coercion. Preserve valid geometry with a specific geometry-only reason when atomic information is unusable. Optional metadata must remain optional, including species information that the supported backend can validly infer from labels. Add both reproductions as regression cases.

### 3. [P1] The data-block guard can still silently merge structures

Location: [cif_adapter.py](/Users/hongxunyang/workplace/tools/advisor/advisor/domain/cif_import/cif_adapter.py:39), used before parsing at line 74.

The raw-text regex recognizes `data_` only at column zero and does not distinguish structural tokens from semicolon-delimited text.

**Reproduced:** append these lines to the high-precision fixture:

```cif
  data_second
_cell_length_a 7.0
```

Import returns `ready`, identifies the source as `high_precision_test`, but reports `a = 7.0` from the second block while retaining the first block's other cell values and atoms. This is exactly the silent merge the requirement forbids.

Conversely, a single-block file with the following ordinary text field is rejected as containing two structures:

```cif
_publ_section_comment
;
Example block name:
data_example
;
```

**Required correction:** determine blocks through CIF-aware parsing/tokenization that respects whitespace and text fields. Keep the agreed policy of rejecting genuine multiple blocks; a block picker is unnecessary. Do not fix only the leading-space regex and leave the text-field problem. Add both examples and verify that no consumer receives merged input.

### 4. [P1] Initialization errors escape through the Qt signal instead of reaching the error dialog

Location: [AppController.apply_parameters](/Users/hongxunyang/workplace/tools/advisor/advisor/controllers/app_controller.py:67); connection at line 49 and emission in [InitWindow.initialize](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/init_window.py:544).

The rollback itself clears global parameters, but re-raising from a slot connected to a PyQt signal does not propagate the exception back into the Python `try/except` surrounding `initialized.emit()`. The log's explanation of the recovery path is incorrect.

**Reproduced:** inject a failure into the second feature's `set_parameters()` and call the real `InitWindow.initialize()`. A recording `sys.excepthook` receives the exception; `QMessageBox.critical` receives zero calls. Global parameters become `None`, but the promised recoverable user error is absent. The recording hook prevented an unhandled exception from terminating the diagnostic process; this was not a direct call to `apply_parameters()`.

**Required correction:** handle/report failures at the slot boundary, or return a structured application result through a synchronous controller call that the UI can catch. Preserve the all-features-inactive rollback. Test the real signal/button route, assert one visible error and no unhandled exception, then verify a successful retry.

## Important — remaining requirement gaps and regressions

### 5. [P2] Atomic previews can show fabricated atoms or retain the previous image

Locations: [InitWindow.on_structure_changed](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/init_window.py:394), [scattering preview loading](/Users/hongxunyang/workplace/tools/advisor/advisor/features/scattering_geometry/ui/scattering_geometry_tab.py:149), and [UnitcellVisualizer.set_parameters / visualize_unitcell](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/visualizers/unitcell_visualizer.py:71).

Two parts of the preview contract remain incomplete:

- **Geometry-only input:** importing the provided `cell_only.cif` correctly sets `structure_factor_ok=False`, but the setup preview still constructs a `Crystal` because `geometry_ok=True`. The resulting initialized preview contains a synthetic `Fe` atom. Geometry capability does not establish that atomic positions are available. Scattering-tab previews also reopen any supplied CIF without this distinction.
- **Backend loading failure:** `set_parameters()` records `render_error_message`, clears the model, and marks it uninitialized, but does not clear the existing artists. `visualize_unitcell()` then returns before rendering the message. After a valid preview followed by an injected backend loading exception, the image remained byte-for-byte identical, all six previous atom/cell artists remained, and the only visible texts were `a`, `b`, `c`.

**Required correction:** render atoms only when validated atomic information supports the preview; otherwise show the real cell alone or a concise unavailable message. An unsupported structure-factor calculation need not prohibit a genuinely supported atomic preview, so use the actual capability rather than assuming all capabilities are identical. On load failure, clear both old model and graphics and render the error state. Test cell-only input and successful preview → loading failure, including the visible canvas rather than only `render_error_message`.

### 6. [P2] UB fitting still uses rounded spinbox values

Locations: [open_diffraction_test_dialog](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/init_window.py:290), [setup visualization](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/init_window.py:459), and [_current_ub_data](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/init_window.py:494).

Global Initialize correctly uses `StructureSource`, but these other consumers still read the widgets. `HighPrecisionSpinBox` does not remove `QDoubleSpinBox`'s configured precision/range limits.

**Reproduced:** for the supplied high-precision fixture, accepted source and global calculation parameter `a` are `5.431020511`, while the widget and the lattice passed into `DiffractionTestDialog` are `5.431021`. UB validity checking also compares against the rounded widget lattice. The sample's difference is small, but it violates the explicit common-cell contract; values outside the display widgets' ranges can be clamped as well.

**Required correction:** centralize retrieval of the effective setup lattice: accepted full-precision values for CIF mode, editable values for manual mode. Use it consistently for Initialize, UB inputs/validity, and setup geometry rendering. Keep candidate/applied semantics and the fitting algorithm unchanged. Extend the precision test through the UB dialog boundary and actual backend cell, not just source storage.

### 7. [P2] Temporary CIF snapshots have no production cleanup owner

Locations: [CifImportService.prepare_from_path](/Users/hongxunyang/workplace/tools/advisor/advisor/controllers/cif_import_service.py:25), [AppController.import_cif](/Users/hongxunyang/workplace/tools/advisor/advisor/controllers/app_controller.py:100), and [snapshot I/O](/Users/hongxunyang/workplace/tools/advisor/advisor/domain/cif_import/io.py:49).

Every readable candidate creates a new temporary directory before validation. Rejection and identical-content reselection leave it behind. Replacement, manual transition, removal, Reset, and app shutdown do not release accepted snapshots either. `cleanup_snapshot()` exists, but production code never calls it; tests call it themselves and therefore do not verify application ownership.

**Reproduced in an isolated temporary root:** import A → reselect A → reject a malformed file → Reset leaves three additional `advisor_cif_*` directories. This contradicts the log's “one ... snapshot per accepted structure” description and accumulates full source copies during routine use.

**Required correction:** give temporary snapshots an explicit session owner. Dispose of rejected/no-op candidates, release superseded snapshots after their consumers are invalidated, and clean owned session files on normal shutdown. Handle partial-write failure too. Delete only directories created/owned by this infrastructure; never infer ownership from an arbitrary input path. Test lifecycle cleanup without manually cleaning application-owned snapshots in the assertion path, and ensure active snapshots remain usable after the original file is removed.

### 8. [P2] The file field shows rejected or removed input as if it were selected

Locations: [CifDropTarget._select](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/components/cif_selector.py:110) and [InitWindow.on_structure_changed](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/init_window.py:377).

`_select()` writes the candidate path before acceptance. The accepted-state render never restores, updates, or clears it. Imports from the menu/dialog also do not synchronize this field.

**Reproduced:** select bundled `nacl.cif`, then select `malformed.cif`. The accepted source remains NaCl, while the file field shows `malformed.cif`. Remove CIF clears the accepted source but leaves the malformed path visible. The captured setup window also showed an old malformed path next to the newly accepted high-precision structure name.

**Required correction:** render this field from accepted state, with candidate failures presented separately and clearly. Synchronize drop, Browse, menu, dialog, manual transition, and removal. Re-selecting the accepted file after a rejection should restore its readiness feedback without invalidating scientific state. Test through the selector's actual selection method/Browse route; emitting `cifSelected` directly misses the premature display mutation.

### 9. [P2] Adding scan clearing accidentally removed the accessibility overlay's redraw

Location: [HKLScan2DVisualizer](/Users/hongxunyang/workplace/tools/advisor/advisor/ui/visualizers/HKLScan2DVisualizer.py:257).

The previous `self.draw(); return True` at the end of `plot_accessible_area()` is now inside the newly inserted `clear_plot()`, which consequently draws twice. The scan workflow draws the trajectory first, adds the accessible region second, and performs no subsequent redraw.

**Reproduced:** calling `plot_accessible_area()` adds artists but leaves the rendered canvas unchanged and returns `None`. A separate explicit `draw()` makes the accessible region appear. The overlay can therefore remain absent until a later redraw such as resizing.

**Required correction:** restore the overlay method's redraw/return behavior and keep one draw in `clear_plot()`. Add a targeted scan/overlay rendering check; the new clearing test does not cover this regression.

## Layout acceptance: existing constraint, still unresolved

I rendered the assembled `MainWindow` with its real stacked pages, application QSS, English locale, and the startup high-DPI settings. Requested and actual logical sizes were:

| Requested application size | Actual current size |
| --- | --- |
| 1100 × 700 | 1301 × 702 |
| 1280 × 800 | 1301 × 800 |
| 1440 × 900 | 1440 × 900 |

The untouched baseline at `c28d36e` produced the same results. **This is a pre-existing constraint, not a width regression introduced by this implementation.** Nevertheless, REQUIREMENT_1's small-window acceptance target is not established. Rendering each page separately, as the log describes, misses the combined minimum-size constraints from the assembled window and hidden pages.

Verify and address the constraint in the actual application shell before declaring the MacBook Air layout requirement complete. Preserve the existing visual language and plot emphasis; do not enlarge the minimum window to satisfy the check. Repeat loaded, empty, geometry-only, error, and dialog states. These measurements are from Qt offscreen rendering and do not establish native macOS menu/dock/Retina usability; an interactive check remains outstanding.

## Architecture assessment

Keep the overall implementation structure: shared non-Qt source/result/capability types, a small preparation service, accepted-state ownership in `AppController`, and feature-owned invalidation are appropriate. Removing the duplicated importer and routing the menu through the same entry point are worthwhile. Exact source snapshots also preserve the right boundary against external file edits.

No broad rewrite or generic import framework is warranted. The necessary structural changes are narrow: explicit calculator rebinding to child consumers, explicit snapshot ownership/disposal, one authoritative lattice accessor, and a parser/capability boundary that validates what consumers actually use. Retain independent mutable backend instances and the existing immutable reflection-export snapshots.

After the fixes, correct the log and relevant `.cursor` contracts: raw-key checks do not establish atomic readiness; re-raising a Qt slot exception does not invoke the emitter's error handler; the child calculator is not currently rebound; snapshot cleanup is not currently automatic; and spinbox values are not the accepted full-precision lattice. Document verified behavior rather than the intended guarantees.

## Verification performed and completion gate

- Read `REQUIREMENT_1.md`, `IMPLEMENTATION_LOG.md`, `CLAUDE.md`, relevant `.cursor` rules, implementation diffs, affected consumers, new tests, and the installed Dans_Diffraction parsing/atom-loading code.
- Ran the full suite with offscreen Qt: **651 passed, 6 warnings, 45.15 seconds**. This confirms the log's test count for this checkout.
- Ran additional temporary probes with real controllers, widgets, CIF parsing, and structure-factor calculation. These reproduced findings 1–3 and 5–9. Used deliberate failure injection through the real Qt signal for finding 4 and into preview loading for finding 5; these are fault-path tests, not claims that a normal valid import raises those exceptions.
- Rendered and inspected the integrated setup window, measured the three application sizes, and compared the same layout probe with the baseline. No interactive drag/drop or real-display MacBook Air testing was performed.

The passing suite misses child-held calculator references, usable atom content, CIF lexical block boundaries, exceptions crossing Qt signals, UB's real input precision, production snapshot cleanup, displayed selection identity, and the overlay redraw. Add focused behavioral regression coverage for these boundaries, rerun the full suite, and verify the assembled UI. Keep REQUIREMENT_2's library, examples, and persistence work out of this correction pass.
