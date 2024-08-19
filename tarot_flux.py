import io
from pathlib import Path
from pydantic import BaseModel
from typing import List
import modal

sdxl_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(
        "libglib2.0-0", "libsm6", "libxrender1", "libxext6", "ffmpeg", "libgl1"
    )
    .pip_install(
        "diffusers==0.30.0",
        "invisible_watermark==0.2.0",
        "transformers~=4.38.2",
        "accelerate",
        "safetensors",
        "sentencepiece",
        "peft==0.11.1"
    )
)

app = modal.App("tarot-lora")

with sdxl_image.imports():
    import torch
    from diffusers import DiffusionPipeline
    from fastapi import Response

@app.cls(gpu=modal.gpu.A100(), container_idle_timeout=240, image=sdxl_image, secrets=[modal.Secret.from_name("HF_TOKEN")])
class Model:
    @modal.build()
    def build(self):
        from huggingface_hub import snapshot_download

        ignore = [
            "*.bin",
            "*.onnx_data",
            "*/diffusion_pytorch_model.safetensors",
        ]

        snapshot_download(
            "black-forest-labs/FLUX.1-dev", ignore_patterns=ignore
        )
        snapshot_download(
            "multimodalart/flux-tarot-v1", ignore_patterns=ignore
        )

    @modal.enter()
    def enter(self):
        # Load base model
        self.base = DiffusionPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16,
        ).to("cuda")

        self.base.load_lora_weights("multimodalart/flux-tarot-v1")

        # Compiling the model graph is JIT so this will increase inference time for the first run
        # but speed up subsequent runs. Uncomment to enable.
        # self.base.unet = torch.compile(self.base.unet, mode="reduce-overhead", fullgraph=True)
        # self.refiner.unet = torch.compile(self.refiner.unet, mode="reduce-overhead", fullgraph=True)

    def _inference(self, prompt, n_steps=24, high_noise_frac=0.8):
        width = 768
        height = 1024
        seed = 0
        lora_scale = 0.95
        cfg_scale = 3.5

        trigger_word = "in the style of TOK a trtcrd, tarot style"

        generator = torch.Generator(device="cuda").manual_seed(seed)
    
        image = self.base(
            prompt=f"{prompt} {trigger_word}",
            num_inference_steps=n_steps,
            guidance_scale=cfg_scale,
            width=width,
            height=height,
            generator=generator,
            joint_attention_kwargs={"scale": lora_scale},
        ).images[0]

        byte_stream = io.BytesIO()
        image.save(byte_stream, format="JPEG")

        return byte_stream

    @modal.method()
    def inference(self, prompt, n_steps=24, high_noise_frac=0.8):
        return self._inference(
            prompt, n_steps=n_steps, high_noise_frac=high_noise_frac
        ).getvalue()

    @modal.web_endpoint(docs=True)
    def web_inference(
        self, prompt: str, n_steps: int = 24, high_noise_frac: float = 0.8
    ):
        return Response(
            content=self._inference(
                prompt, n_steps=n_steps, high_noise_frac=high_noise_frac
            ).getvalue(),
            media_type="image/jpeg",
        )
    
@app.local_entrypoint()
def main(prompt: str = "The personification of middle managment saying middle management on the card"):
    image_bytes = Model().inference.remote(prompt)

    dir = Path("/tmp/flux-lora-v1")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    output_path = dir / "output.png"
    print(f"Saving it to {output_path}")
    with open(output_path, "wb") as f:
        f.write(image_bytes)

class MinorArcanaSuit:
    name: str 
    description: str 

class Arcana:
    name: str
    description: str 
    divinatory_meaning: str 
    reversed: str

frontend_path = Path(__file__).parent / "frontend"

web_image = modal.Image.debian_slim().pip_install("jinja2")

@app.function(
    image=web_image,
    mounts=[modal.Mount.from_local_dir(frontend_path, remote_path="/assets")],
    allow_concurrent_inputs=20,
)
@modal.asgi_app()
def ui():
    import fastapi.staticfiles
    from fastapi import FastAPI, Request
    from fastapi.templating import Jinja2Templates

    web_app = FastAPI()
    templates = Jinja2Templates(directory="/assets")

    @web_app.get("/")
    async def read_root(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "inference_url": Model.web_inference.web_url,
                "model_name": "Stable Diffusion XL",
                "default_prompt": "A cinematic shot of a baby raccoon wearing an intricate italian priest robe.",
            },
        )

    web_app.mount(
        "/static",
        fastapi.staticfiles.StaticFiles(directory="/assets"),
        name="static",
    )

    return web_app