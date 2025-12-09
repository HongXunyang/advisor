Appendix
========

Scattering angles, momentum transfer HKL
-----------------------

**Scattering angles**:

.. image:: _static/angles.png
   :width: 80%
   :alt: Screenshot of the rotation order.
   :class: with-border
   :align: center



#. **tth (2θ)** — the scattering angle between the incoming and outgoing beam.
#. **θ** — primary/base rotation; axis fixed in the laboratory frame.
#. **χ** — secondary/tilt rotation; stage is mounted on top of the θ stage, so the axis depends on θ.
#. **φ** — tertiary/sample azimuth; stage is mounted on top of χ, so the axis depends on θ then χ.

Rotations are applied in stack order (θ → χ → φ):

.. math::

   R_{\text{total}} = R_{\theta}\, R_{\chi}\,  R_{\phi}




**Momentum transfer and HKL**:

.. image:: _static/hkl_rep.png
   :width: 60%
   :alt: Screenshot of the HKL representation.
   :class: with-border
   :align: center

**H, K, L (r.l.u.)** — components of the momentum transfer :math:`\mathbf{Q}` in the reciprocal lattice basis.

.. math::

   \mathbf{Q} = H\,\mathbf{a}^* + K\,\mathbf{b}^* + L\,\mathbf{c}^*

Given real-space vectors :math:`\mathbf{a}, \mathbf{b}, \mathbf{c}` and volume :math:`V = \mathbf{a}\cdot(\mathbf{b}\times\mathbf{c})`:

.. math::

   \mathbf{a}^* = 2\pi\frac{\mathbf{b}\times\mathbf{c}}{V},\quad
   \mathbf{b}^* = 2\pi\frac{\mathbf{c}\times\mathbf{a}}{V},\quad
   \mathbf{c}^* = 2\pi\frac{\mathbf{a}\times\mathbf{b}}{V}

From a Cartesian :math:`\mathbf{Q}`, the r.l.u. are:

.. math::

   H=\frac{\mathbf{Q}\cdot\mathbf{a}^*}{2\pi},\quad
   K=\frac{\mathbf{Q}\cdot\mathbf{b}^*}{2\pi},\quad
   L=\frac{\mathbf{Q}\cdot\mathbf{c}^*}{2\pi}


----

Structure factor planes (U/V/Center)
------------------------------------
The two vectors :math:`\mathbf{U}` and :math:`\mathbf{V}` span a plane in reciprocal space. The vector :math:`\mathbf{Q}_0` is the center of the plane. The U and V ranges control the size of the sampled plane in reciprocal space.

- **U vector** — in r.l.u., defines one in-plane direction. For example, ``1,1,0`` means 
.. math::
   \mathbf{U} = 1\,\mathbf{a}^* + 1\,\mathbf{b}^* + 0\,\mathbf{c}^*
- **V vector** — in r.l.u., defines the other in-plane direction. For example, ``0,0,1`` means 
.. math::
   \mathbf{V} = 0\,\mathbf{a}^* + 0\,\mathbf{b}^* + 1\,\mathbf{c}^*
- **Center** — HKL coordinates of the plane’s center point. For example, ``2,2,2`` means 
.. math::
   \mathbf{Q}_0 = 2\,\mathbf{a}^* + 2\,\mathbf{b}^* + 2\,\mathbf{c}^*
- **U range / V range** — extents along U and V from the center (symmetric about the center) controlling the size of the sampled plane in reciprocal space.

Use the U/V/Center inputs in the Structure Factor tab to pick an oriented plane through reciprocal space and set how wide the sampled region is along each in-plane axis.


Quick links
-----------
- See :doc:`using_app` for step-by-step UI usage.