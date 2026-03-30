import re


class FilePathBuilder:
    MAX_FOLDER_VARS = 5
    MAX_FILENAME_VARS = 5

    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "folder_template": ("STRING", {"default": "{shotname}/", "multiline": False}),
            },
        }
        for i in range(1, s.MAX_FOLDER_VARS + 1):
            inputs["required"][f"folder_var_{i}"] = ("STRING", {"default": "", "multiline": False})
        inputs["required"]["filename_template"] = ("STRING", {"default": "{shotname}_{artist}_v", "multiline": False})
        for i in range(1, s.MAX_FILENAME_VARS + 1):
            inputs["required"][f"filename_var_{i}"] = ("STRING", {"default": "", "multiline": False})
        inputs["required"]["force_uppercase"] = ("BOOLEAN", {"default": False})
        inputs["hidden"] = {
            "unique_id": "UNIQUE_ID",
            "extra_pnginfo": "EXTRA_PNGINFO",
        }
        return inputs

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("filename", "full_path")
    FUNCTION = "build_path"
    OUTPUT_NODE = True
    CATEGORY = "File Management"

    @staticmethod
    def _parse_variables(template):
        return list(dict.fromkeys(re.findall(r"\{(\w+)\}", template)))

    def build_path(self, folder_template, filename_template, force_uppercase,
                   unique_id=None, extra_pnginfo=None, **kwargs):
        # Parse variables for each template separately
        folder_vars = self._parse_variables(folder_template)
        filename_vars = self._parse_variables(filename_template)

        # Map folder variable names to folder_var_ slot values
        folder_map = {}
        for i, var_name in enumerate(folder_vars):
            slot_key = f"folder_var_{i + 1}"
            folder_map[var_name] = kwargs.get(slot_key, "").strip()

        # Map filename variable names to filename_var_ slot values
        # Skip variables already defined in folder_map (reuse folder values)
        filename_map = {}
        filename_slot_idx = 0
        for var_name in filename_vars:
            if var_name in folder_map:
                filename_map[var_name] = folder_map[var_name]
            else:
                filename_slot_idx += 1
                slot_key = f"filename_var_{filename_slot_idx}"
                filename_map[var_name] = kwargs.get(slot_key, "").strip()

        # Build folder path
        folder_path = folder_template
        for name, value in folder_map.items():
            folder_path = folder_path.replace("{" + name + "}", value)
        folder_path = "/".join(p for p in folder_path.split("/") if p.strip())

        # Build filename
        filename = filename_template
        for name, value in filename_map.items():
            filename = filename.replace("{" + name + "}", value)
        filename = re.sub(r"([_\-.])\1+", r"\1", filename)
        filename = filename.strip("_-.")

        if force_uppercase:
            filename = filename.upper()

        # Combine
        if folder_path and filename:
            full_path = folder_path + "/" + filename
        elif folder_path:
            full_path = folder_path
        else:
            full_path = filename

        return {"ui": {"text": [full_path]}, "result": (filename, full_path)}


NODE_CLASS_MAPPINGS = {
    "FilePathBuilder": FilePathBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FilePathBuilder": "File Path Builder v2",
}
