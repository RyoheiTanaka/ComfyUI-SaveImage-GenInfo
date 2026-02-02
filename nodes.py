import json
import os

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths


class SaveImageWithGenInfo:
    """
    ComfyUI Save Image node with A1111-compatible generation info.
    Automatically extracts settings from the workflow and embeds them
    as JSON metadata in the PNG file.
    """

    SAMPLER_KEYS = ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"]
    SAMPLER_ADVANCED_KEYS = [
        "noise_seed", "steps", "cfg", "sampler_name", "scheduler",
        "start_at_step", "end_at_step", "add_noise",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            },
            "optional": {
                "filename_prefix": ("STRING", {"default": "GenStash"}),
                "foldername": ("STRING", {"default": ""}),
                "save_metadata": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("generation_info_json",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "GenStash"

    # ------------------------------------------------------------------
    # 生成情報の抽出
    # ------------------------------------------------------------------

    def _extract_generation_info(self, prompt):
        info = {}

        if not prompt:
            return info

        for _node_id, node_data in prompt.items():
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})

            if class_type == "KSampler":
                for key in self.SAMPLER_KEYS:
                    if key in inputs and not isinstance(inputs[key], list):
                        info[key] = inputs[key]

            elif class_type == "KSamplerAdvanced":
                for key in self.SAMPLER_ADVANCED_KEYS:
                    if key in inputs and not isinstance(inputs[key], list):
                        out_key = "seed" if key == "noise_seed" else key
                        info[out_key] = inputs[key]

            elif class_type == "CheckpointLoaderSimple":
                if "ckpt_name" in inputs:
                    info["model"] = inputs["ckpt_name"]

            elif class_type == "CLIPTextEncode":
                text = inputs.get("text", "")
                if isinstance(text, str) and text:
                    role = self._resolve_prompt_role(_node_id, prompt)
                    if role == "negative":
                        info["negative_prompt"] = text
                    else:
                        if "prompt" not in info:
                            info["prompt"] = text

            elif class_type == "EmptyLatentImage":
                if "width" in inputs and not isinstance(inputs["width"], list):
                    info["width"] = inputs["width"]
                if "height" in inputs and not isinstance(inputs["height"], list):
                    info["height"] = inputs["height"]

            elif class_type == "CLIPSetLastLayer":
                val = inputs.get("stop_at_clip_layer")
                if val is not None and not isinstance(val, list):
                    info["clip_skip"] = abs(val)

        if "sampler_name" in info and "scheduler" in info:
            info["sampler"] = f"{info['sampler_name']} {info['scheduler']}"

        if "width" in info and "height" in info:
            info["size"] = f"{info['width']}x{info['height']}"

        return info

    def _resolve_prompt_role(self, clip_node_id, prompt):
        for _nid, node_data in prompt.items():
            class_type = node_data.get("class_type", "")
            if class_type not in ("KSampler", "KSamplerAdvanced"):
                continue
            inputs = node_data.get("inputs", {})

            pos = inputs.get("positive")
            if isinstance(pos, list) and str(pos[0]) == str(clip_node_id):
                return "positive"

            neg = inputs.get("negative")
            if isinstance(neg, list) and str(neg[0]) == str(clip_node_id):
                return "negative"

        return "positive"

    # ------------------------------------------------------------------
    # メイン処理
    # ------------------------------------------------------------------

    def save(self, images, filename_prefix="GenStash", foldername="",
             save_metadata=True, prompt=None, extra_pnginfo=None):

        # 生成情報を抽出
        gen_info = self._extract_generation_info(prompt)
        gen_info_json = json.dumps(gen_info, ensure_ascii=False)

        # 出力先
        output_base = folder_paths.get_output_directory()
        if foldername:
            output_folder = os.path.join(output_base, foldername)
        else:
            output_folder = output_base
        os.makedirs(output_folder, exist_ok=True)

        # カウンター用にComfyUI標準の仕組みを利用
        subfolder = foldername if foldername else ""
        full_output_folder, filename, counter, subfolder_out, _ = (
            folder_paths.get_save_image_path(
                filename_prefix, output_base,
                images[0].shape[1], images[0].shape[0]
            )
        )

        if foldername:
            full_output_folder = output_folder

        results = []
        for batch_idx, image in enumerate(images):
            img_array = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))

            metadata = PngInfo()

            if save_metadata:
                metadata.add_text("generation_info", gen_info_json)

                if extra_pnginfo:
                    for key, value in extra_pnginfo.items():
                        metadata.add_text(key, json.dumps(value))

            fname = f"{filename_prefix}_{counter + batch_idx:05d}.png"
            filepath = os.path.join(full_output_folder, fname)
            img.save(filepath, pnginfo=metadata)

            results.append({
                "filename": fname,
                "subfolder": subfolder,
                "type": "output",
            })

        return {
            "result": (gen_info_json,),
            "ui": {"images": results},
        }


NODE_CLASS_MAPPINGS = {
    "SaveImageWithGenInfo": SaveImageWithGenInfo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithGenInfo": "Save Image (GenStash)",
}
