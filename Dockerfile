FROM debian:bookworm-slim AS llama-builder

ARG LLAMA_CPP_REVISION=720d7fa4097f76e5d0eade5a92c1df87c1faf9d9

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    git \
    libcurl4-openssl-dev \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/ggml-org/llama.cpp.git /src/llama.cpp \
    && git -C /src/llama.cpp checkout "${LLAMA_CPP_REVISION}"

RUN cmake -S /src/llama.cpp -B /src/llama.cpp/build \
    -DBUILD_SHARED_LIBS=OFF \
    -DGGML_BLAS=ON \
    -DGGML_BLAS_VENDOR=OpenBLAS \
    -DGGML_NATIVE=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_CURL=ON \
    && cmake --build /src/llama.cpp/build --config Release --target llama-server -j2

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libcurl4 \
    libgomp1 \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 user

COPY --from=llama-builder /src/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server

ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    VAHAAN_MANIFEST=/app/release/manifest.yaml \
    VAHAAN_MODEL_CACHE=/home/user/.cache/vaahan/models \
    PYTHONUNBUFFERED=1 \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app
COPY --chown=user:user pyproject.toml README.md LICENSE ./
COPY --chown=user:user src ./src
COPY --chown=user:user release ./release

RUN pip install --no-cache-dir .

USER user
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health/live', timeout=3)"

CMD ["uvicorn", "vaahan.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--proxy-headers"]

