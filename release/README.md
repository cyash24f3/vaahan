# SETU release manifest

`manifest.yaml` is the only model-selection input used by VAHAAN. It pins the
base GGUF revision and checksum, the converted LoRA checksum, the prompt and
schema versions, runtime limits, and the release evaluation report.

The 2.2 MB LoRA adapter is committed with this release. The pinned base model is
downloaded from Hugging Face and verified before the service becomes ready.

