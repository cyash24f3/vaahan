from vaahan.prompting import build_prompt


def test_prompt_uses_training_contract() -> None:
    prompt = build_prompt("UPI failed")
    assert prompt.startswith("<|im_start|>system\n")
    assert "<|im_start|>user\nUPI failed<|im_end|>" in prompt
    assert prompt.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")
