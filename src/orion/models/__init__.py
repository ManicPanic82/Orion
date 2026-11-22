"""Model Manager, Model Profiles, and model host adapters for Orion."""

from orion.models.compatibility import ensure_valid_profile, validate_profile
from orion.models.errors import (
    AdapterRequiredError,
    ModelLoadError,
    ModelProfileError,
    PartialLoadError,
    ProfileIncompatibleError,
    ProfileNotFoundError,
    ProfileRepositoryError,
    ProfileValidationError,
    UnsupportedBackendError,
)
from orion.models.host import (
    BaseHostAdapter,
    MockHost,
    MockModelHost,
    MockModelHostAdapter,
    ModelHost,
    ModelHostProtocol,
    RuntimeDescription,
)
from orion.models.manager import ModelManager
from orion.models.profile import (
    SCHEMA_VERSION as PROFILE_SCHEMA_VERSION,
)
from orion.models.profile import (
    AdapterMode,
    AdapterRef,
    AdapterRequirement,
    AdapterState,
    AdapterStatus,
    BaseModelRef,
    ModelProfile,
    TokenizerRef,
)
from orion.models.repository import (
    InMemoryProfileRepository,
    JsonProfileRepository,
    ProfileRepository,
)
from orion.models.state import (
    ModelLoadState,
    ModelManagerState,
    ModelManagerStatus,
    ModelStatusState,
    ProfileLoadState,
)

__all__ = [
    "AdapterMode",
    "AdapterRef",
    "AdapterRequirement",
    "AdapterState",
    "AdapterStatus",
    "BaseHostAdapter",
    "BaseModelRef",
    "InMemoryProfileRepository",
    "JsonProfileRepository",
    "MockHost",
    "MockModelHost",
    "MockModelHostAdapter",
    "ModelHost",
    "ModelHostProtocol",
    "ModelLoadState",
    "ModelManager",
    "ModelManagerState",
    "ModelManagerStatus",
    "ModelProfile",
    "ModelProfileError",
    "ModelStatusState",
    "PartialLoadError",
    "ProfileIncompatibleError",
    "ProfileLoadState",
    "ProfileNotFoundError",
    "ProfileRepository",
    "ProfileRepositoryError",
    "ProfileValidationError",
    "PROFILE_SCHEMA_VERSION",
    "RuntimeDescription",
    "TokenizerRef",
    "UnsupportedBackendError",
    "AdapterRequiredError",
    "ModelLoadError",
    "SCHEMA_VERSION",
    "PROFILE_SCHEMA_VERSION",
    "ensure_valid_profile",
    "validate_profile",
]
# Backwards/alias friendly names.
ModelProfileManifest = ModelProfile
ModelProfileVersion = ModelProfile
ProfileManager = ModelManager
ModelManagerAlias = ModelManager
SCHEMA_VERSION = PROFILE_SCHEMA_VERSION
PROFILE_SCHEMA_VERSION = PROFILE_SCHEMA_VERSION
