---
title: SETU x VAHAAN
emoji: 🛺
colorFrom: green
colorTo: orange
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
license: mit
---

# VAHAAN

VAHAAN is the portable serving and release-engineering layer for
[SETU](https://github.com/cyash24f3/setu), a Qwen3.5-2B model fine-tuned to
turn Hinglish and English e-commerce messages into one strict ten-field JSON
object.

The project exists because SETU was trained with MLX QLoRA on Apple silicon,
while the public demo runs on Linux CPU hardware. VAHAAN converts and validates
that boundary instead of pretending a local MLX model is directly portable.

## What the service guarantees

- One reviewed manifest selects the exact base, adapter, prompt, schema, and
  runtime.
- SHA-256 verification occurs before readiness becomes true.
- The model loads once and is never reloaded per request.
- Requests are length-bounded and concurrency is bounded to one model slot.
- Model output must be valid JSON and pass the exact Pydantic schema.
- Invalid output returns a typed 502 response; fields are never fabricated.
- Normal logs contain request metadata and latency, not the customer message.
- Liveness, readiness, version, OpenAPI, and Prometheus endpoints are separate.
- The container runs as a non-root user.

## Release architecture

```text
Browser UI
   │
   ▼
FastAPI contract ── rate limit / optional API key
   │
   ▼
Analysis service ── bounded queue / strict parser / metrics
   │
   ▼
Pinned llama.cpp server
   │
   ├── Qwen3.5-2B GGUF base at an immutable Hub revision
   └── SETU LoRA GGUF adapter verified by checksum
```

The API and model process are intentionally separate. HTTP routes do not know
tensor details, and the inference backend does not decide HTTP status codes.

## API

`POST /v1/analyze`

Request:

```json
{"message": "UPI se payment fail ho rahi hai, please help"}
```

Success responses contain the validated ten-field result and release metadata.
Operational endpoints:

- `/health/live`
- `/health/ready`
- `/v1/version`
- `/docs`
- `/metrics`

## The selected artifact

The first release uses Qwen3.5-2B Q8_0 with a converted F16 LoRA adapter. Q8_0
is larger than Q4_K_M, but the release choice is based on SETU canary quality
rather than selecting the smallest fashionable quantization. The exact
comparison is stored in the SETU reports.

The container is designed for a 2-vCPU, 16-GB Linux CPU target. As of July
2026, Hugging Face requires a paid personal plan to create a new Docker compute
Space, so the free public release uses a static evidence site with recorded
schema-validated canaries. Local Apple Metal latency is never presented as
hosted CPU latency.

Public links:

- Evidence site: https://setu-vaahan.witty-loon-6439.chatgpt.site
- Hugging Face Space: https://huggingface.co/spaces/cyash1204/setu-vaahan
- Model and adapters: https://huggingface.co/cyash1204/setu-qwen35-2b-lora
- Dataset: https://huggingface.co/datasets/cyash1204/setu-hinglish-support-6000

## Local development

Requirements:

- Python 3.12
- a current `llama-server` binary with Qwen3.5 support
- enough disk space for the pinned GGUF

Install and run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make check
make run
```

The first real-model startup downloads the pinned base artifact. Set
`VAHAAN_LLAMA_BINARY` when `llama-server` is not on `PATH`.

## Testing tiers

The normal CI path runs without a model:

- schema and hierarchy unit tests;
- manifest and checksum tests;
- prompt-contract tests;
- queue, parser, and service tests;
- complete FastAPI contract tests with a deterministic fake backend;
- linting, formatting, and strict type checking.

Release validation additionally runs the 50-scenario real-model equivalence
canary and the full SETU evaluation at the model-release boundary.

## Security and privacy

The public portfolio UI is intentionally unauthenticated and rate-limited in
memory. `VAHAAN_API_KEY` enables header authentication for private deployments.
An in-memory limiter is not sufficient for multiple replicas; a distributed
deployment would move rate state to Redis or the API gateway.

Do not enter real personal details, order IDs, or payment information. This is
a student portfolio system trained on synthetic data, not a customer-support
service.

## Known limitations

- Synthetic training data does not prove real-traffic generalization.
- Language-mix classification is SETU's weakest field.
- The free public showcase does not execute model inference; it replays three
  recorded release canaries and links to the reproducible container service.
- A live CPU host needs roughly 2 GB for the Q8 base plus runtime overhead and
  is outside the currently available no-cost compute tiers.
- Live accuracy cannot be monitored without reviewed labels; distribution
  drift is only a signal.
