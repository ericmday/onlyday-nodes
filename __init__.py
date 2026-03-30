from typing_extensions import override
from comfy_api.latest import ComfyExtension, io

from .keyframe_burnin import KeyframeBurnIn
from .file_path_builder import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]


class OnlyDayExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [KeyframeBurnIn]


async def comfy_entrypoint() -> OnlyDayExtension:
    return OnlyDayExtension()
