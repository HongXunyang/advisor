Overview
========

The Ad-VISOR is a python-based desktop GUI application for scattering and diffraction experiments. It visualizes
the scattering geometry, momentum transfer in reciprocal space, and more. Currently it is tailored
for X-ray scattering and X-ray diffraction experiments. 

What it does
------------
- Visualize scattering geometry and crystal structure.
- Convert scattering angles to momentum transfer in reciprocal space and vice versa.
- Calculate and visualize structure factors for diffraction experiments.

Graphical user interface
------------------------

The following video shows a demostration of the application, giving an overview of the functionality
and user experience.


.. raw:: html

   <video controls width="600" style="margin: 1em 0; border-radius: 8px; box-shadow: 0 2px 12px #0002;">
     <source src="_static/showcase.mp4" type="video/mp4">
     Your browser does not support the video tag.
   </video>




----


Layout at a glance
------------------
.. code-block:: none

    advisor/          application package
        app.py        bootstrap
        controllers/  app/feature coordinators
        domain/       math and geometry helpers (no PyQt)
        features/     per-feature domain/controller/ui code
        ui/           shared UI pieces (init window, main window, base tab, visualizers)
        resources/    QSS, icons, config JSON, sample data
    docs/             Sphinx sources (this folder)


