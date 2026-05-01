FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

ARG PYTORCH_VERSION=2.3.0
ARG CUDA_VERSION=12.1.1

LABEL com.nvidia.volumes.needed=nvidia_driver

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTORCH_VERSION=2.3.0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64
ENV STABLE_DIFFUSION_REPO=https://github.com/comp6062/Stability-AI-stablediffusion.git
ENV GIT_TERMINAL_PROMPT=0

RUN apt-get update && apt-get install -y \
    git wget curl libgl1 libglib2.0-0 \
    fonts-dejavu-core ffmpeg pkg-config \
    libcairo2 libcairo2-dev build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git config --global credential.helper "" && \
    git config --global url."https://".insteadOf git://

WORKDIR /app
RUN git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git /app

RUN mkdir -p repositories && \
    git -c credential.helper= clone https://github.com/comp6062/Stability-AI-stablediffusion.git repositories/stable-diffusion-stability-ai && \
    git -c credential.helper= clone https://github.com/Stability-AI/generative-models.git repositories/generative-models && \
    git -c credential.helper= clone https://github.com/crowsonkb/k-diffusion.git repositories/k-diffusion && \
    git -c credential.helper= clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-assets.git repositories/stable-diffusion-webui-assets

RUN pip install --upgrade --force-reinstall "typing_extensions>=4.10.0"
RUN pip install xformers==0.0.26.post1 --index-url https://download.pytorch.org/whl/cu121

ENV CLI_ARGS=
EXPOSE 7860

# --enable-insecure-extension-access allows installing extensions without auth.
# Safe here because the WebUI is LAN-only behind NPM + Tailscale.
# Remove this flag if you expose the port publicly.
# --no-half-vae keeps VAE in full float32 — prevents black/NaN outputs on low-VRAM GPUs like the A2000.
CMD python launch.py --listen --port 7860 \
    --data-dir /data \
    --ckpt-dir /data/models/Stable-diffusion \
    --embeddings-dir /data/embeddings \
    --lora-dir /data/models/Lora \
    --xformers --api --enable-insecure-extension-access \
    --no-half-vae \
    ${CLI_ARGS}
