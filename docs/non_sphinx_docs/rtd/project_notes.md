# Project Notes

This section collects design choices, reminders, and placeholders for richer media when you’re ready to polish the docs.

## Design choices
- **Separation of concerns**: math in `domain/`, PyQt in `ui/`, glue in `controllers/`, per-feature folders in `features/`.
- **No registry file**: features are registered directly in `AppController`, avoiding extra config edits.
- **Reusable visuals**: scattering, unit cell, structure factor, and HKL scan canvases live in `ui/visualizers/`.
- **CIF-first workflow**: dropping a CIF auto-fills lattice parameters and powers structure factor plots; lattice inputs lock after acceptance to keep state consistent.

## Roadmap ideas
- Export results/plots (images, CSV) from tabs.
- Add session save/restore.
- More sample CIFs and preset parameter profiles.

## Media placeholders
- Init window walkthrough: <!-- TODO: insert screenshot/GIF of entering parameters and pressing Initialize. -->
- Brillouin tab demo: <!-- TODO: insert short video showing angles→HKL and geometry update. -->
- Structure factor planes: <!-- TODO: insert image of HKL cube with translucent planes and 2D slices. -->
- Architecture diagram: <!-- TODO: add a small diagram showing domain–controller–view and feature folders. -->

