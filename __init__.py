from .keyframe_burnin import KeyframeBurnIn
from .file_path_builder import NODE_CLASS_MAPPINGS as _FILE_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _FILE_DISPLAY

WEB_DIRECTORY = "./web/js"

NODE_CLASS_MAPPINGS = {
    "KeyframeBurnIn": KeyframeBurnIn,
    **_FILE_MAPPINGS,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KeyframeBurnIn": "Keyframe Burn In",
    **_FILE_DISPLAY,
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
