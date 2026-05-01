import os
import uuid
import sys
from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

MODEL_PATH  = os.environ["MODEL_PATH"]
PROMPT      = os.environ["PROMPT"]
NEG_PROMPT  = os.environ.get("NEGATIVE_PROMPT", "")
STEPS       = int(os.environ.get("STEPS", "30"))
WIDTH       = int(os.environ.get("WIDTH", "1024"))
HEIGHT      = int(os.environ.get("HEIGHT", "1024"))
GUIDANCE    = float(os.environ.get("GUIDANCE_SCALE", "7.5"))
SEED        = os.environ.get("SEED")
USE_XL      = os.environ.get("USE_XL", "auto")

output_dir = Path("/output")
output_dir.mkdir(parents=True, exist_ok=True)
filename = f"{uuid.uuid4()}.png"
output_path = output_dir / filename

# Detect SDXL: explicit flag or infer from filename
is_xl = USE_XL == "1" or (USE_XL == "auto" and "xl" in MODEL_PATH.lower())

if is_xl:
    pipe = StableDiffusionXLPipeline.from_single_file(
        MODEL_PATH,
        torch_dtype=torch.float16,
    )
else:
    pipe = StableDiffusionPipeline.from_single_file(
        MODEL_PATH,
        torch_dtype=torch.float16,
        safety_checker=None,
    )

pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

generator = torch.Generator("cuda").manual_seed(int(SEED)) if SEED else None

image = pipe(
    prompt=PROMPT,
    negative_prompt=NEG_PROMPT,
    num_inference_steps=STEPS,
    width=WIDTH,
    height=HEIGHT,
    guidance_scale=GUIDANCE,
    generator=generator,
).images[0]

image.save(output_path)
print(filename, flush=True)
