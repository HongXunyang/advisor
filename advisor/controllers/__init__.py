"""Controllers coordinating views and domain logic.

Note: `AppController` is deliberately *not* re-exported here. It imports each
feature's controller package, and those import `FeatureController` from this
package — eagerly importing `AppController` in this `__init__.py` would make
importing *any* submodule of `advisor.controllers` (including
`feature_controller` on its own) transitively re-enter a feature controller
package that may still be mid-import, causing a circular-import error.
Import it directly: `from advisor.controllers.app_controller import AppController`.
"""

from .feature_controller import FeatureController

__all__ = ["FeatureController"]
