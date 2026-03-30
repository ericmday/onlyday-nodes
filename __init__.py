import os
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from typing_extensions import override
from comfy_api.latest import ComfyExtension, io


FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DEFAULT_FONT = os.path.join(FONTS_DIR, "FreeMono.ttf")


def _burn_frame_number(pil_img, frame_num, padding_digits, position, font_size,
                       margin, fg_color, bg_color):
    """Burn a frame number onto a single PIL RGBA image, return RGB PIL image."""
    w, h = pil_img.size
    font = ImageFont.truetype(DEFAULT_FONT, font_size)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    text = str(frame_num).zfill(padding_digits)
    # Get the actual bounding box - bbox origin offsets matter at large sizes
    bbox = draw.textbbox((0, 0), text, font=font)
    # bbox = (x_left, y_top, x_right, y_bottom) relative to anchor (0,0)
    bx, by = bbox[0], bbox[1]  # offset from anchor to actual ink
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad = max(4, font_size // 6)  # scale padding with font size

    # Position the anchor point so the ink box lands in the right corner
    if position == "bottom_right":
        # We want ink box's right edge at (w - margin), bottom edge at (h - margin)
        text_x = w - margin - pad - tw - bx
        text_y = h - margin - pad - th - by
    elif position == "bottom_left":
        text_x = margin + pad - bx
        text_y = h - margin - pad - th - by
    elif position == "top_right":
        text_x = w - margin - pad - tw - bx
        text_y = margin + pad - by
    else:  # top_left
        text_x = margin + pad - bx
        text_y = margin + pad - by

    # The actual ink box in image coordinates
    ink_left = text_x + bx
    ink_top = text_y + by

    if bg_color is not None:
        draw.rectangle(
            [ink_left - pad, ink_top - pad, ink_left + tw + pad, ink_top + th + pad],
            fill=bg_color,
        )

    draw.text((text_x, text_y), text, font=font, fill=(*fg_color, 255))
    return Image.alpha_composite(pil_img, overlay).convert("RGB")


COLOR_MAP = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
}

BG_MAP = {
    "semi_transparent_black": (0, 0, 0, 160),
    "semi_transparent_white": (255, 255, 255, 160),
    "solid_black": (0, 0, 0, 255),
    "solid_white": (255, 255, 255, 255),
    "none": None,
}

POSITIONS = ["bottom_right", "bottom_left", "top_right", "top_left"]
COLORS = list(COLOR_MAP.keys())
BACKGROUNDS = list(BG_MAP.keys())


class KeyframeBurnIn(io.ComfyNode):
    """Burns frame numbers onto a batch of images with sequential counting.
    Keyframe images are injected into the batch at their specified frame_idx,
    replacing the original frame at that position. This lets you verify that
    your keyframes land at the correct positions in the sequence."""

    @classmethod
    def define_schema(cls):
        # Build dynamic combo options for 0-20 keyframes
        options = []
        for num_kf in range(0, 21):
            kf_inputs = []
            for i in range(1, num_kf + 1):
                kf_inputs.extend([
                    io.Image.Input(f"keyframe_{i}", tooltip=f"Keyframe image {i} to inject into the sequence"),
                    io.Int.Input(
                        f"frame_idx_{i}",
                        default=0,
                        min=0,
                        max=999999,
                        tooltip=f"Frame position in the batch where keyframe {i} replaces the original frame",
                    ),
                ])
            options.append(io.DynamicCombo.Option(
                key=str(num_kf),
                inputs=kf_inputs,
            ))

        return io.Schema(
            node_id="KeyframeBurnIn",
            display_name="Keyframe Burn In",
            category="image/overlay",
            description="Burns frame numbers onto images. Keyframe images replace frames at their specified positions so you can verify the correct keyframes land in the right spots.",
            inputs=[
                io.Image.Input("images", tooltip="Batch of images to burn sequential frame numbers onto"),
                io.Combo.Input("position", options=POSITIONS, default="bottom_right"),
                io.Int.Input("start_frame", default=0, min=0, max=999999,
                             tooltip="Frame number to start counting from"),
                io.Int.Input("padding_digits", default=4, min=1, max=8,
                             tooltip="Number of digits with leading zeros (4 = 0001)"),
                io.Int.Input("font_size", default=100, min=8, max=256),
                io.Int.Input("margin", default=50, min=0, max=200,
                             tooltip="Pixel margin from image edges"),
                io.Combo.Input("font_color", options=COLORS, default="white"),
                io.Combo.Input("background", options=BACKGROUNDS, default="solid_black"),
                io.DynamicCombo.Input(
                    "keyframes",
                    options=options,
                    display_name="Number of Keyframes",
                    tooltip="Add keyframe images that replace frames at specific positions in the batch",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="images", tooltip="Images with keyframes injected and frame numbers burned in"),
            ],
        )

    @classmethod
    def execute(cls, images, position, start_frame, padding_digits, font_size,
                margin, font_color, background, keyframes) -> io.NodeOutput:
        fg_color = COLOR_MAP[font_color]
        bg_color = BG_MAP[background]
        batch_size = images.shape[0]
        h, w = images.shape[1], images.shape[2]

        # Clone the batch so we can replace frames with keyframes
        batch = images.clone()

        # Inject keyframe images into the batch at their specified positions
        if keyframes:
            kf_keys = sorted([k for k in keyframes.keys() if k.startswith("keyframe_")])
            for kf_key in kf_keys:
                idx = kf_key.split("_")[1]
                img_tensor = keyframes[f"keyframe_{idx}"]
                frame_idx = keyframes[f"frame_idx_{idx}"]

                # frame_idx is the actual frame number; convert to batch index
                batch_idx = frame_idx - start_frame
                if 0 <= batch_idx < batch_size:
                    # Resize keyframe to match batch dimensions if needed
                    kf_frame = img_tensor[0]  # take first frame if batch
                    if kf_frame.shape[0] != h or kf_frame.shape[1] != w:
                        kf_pil = Image.fromarray(
                            (kf_frame.cpu().numpy() * 255).astype(np.uint8)
                        ).resize((w, h), Image.LANCZOS)
                        kf_frame = torch.from_numpy(
                            np.array(kf_pil).astype(np.float32) / 255.0
                        )
                    batch[batch_idx] = kf_frame

        # Burn frame numbers onto every frame in the batch
        out = []
        for i in range(batch_size):
            img_np = (batch[i].cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np).convert("RGBA")
            result = _burn_frame_number(
                pil_img, start_frame + i, padding_digits,
                position, font_size, margin, fg_color, bg_color,
            )
            result_np = np.array(result).astype(np.float32) / 255.0
            out.append(torch.from_numpy(result_np).unsqueeze(0))

        return io.NodeOutput(torch.cat(out, dim=0))


class KeyframeBurnInExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [KeyframeBurnIn]


async def comfy_entrypoint() -> KeyframeBurnInExtension:
    return KeyframeBurnInExtension()
