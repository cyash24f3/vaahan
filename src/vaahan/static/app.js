const fields = [
  "intent", "category", "issue_type", "urgency", "sentiment",
  "language_mix", "order_id", "product_name", "payment_method", "resolution_requested"
];

const message = document.querySelector("#message");
const analyze = document.querySelector("#analyze");
const result = document.querySelector("#result");
const statusText = document.querySelector("#status");
const metadata = document.querySelector("#metadata");
const ready = document.querySelector("#ready");

document.querySelectorAll("[data-message]").forEach((button) => {
  button.addEventListener("click", () => {
    message.value = button.dataset.message;
  });
});

async function checkReady() {
  try {
    const response = await fetch("/health/ready");
    if (response.ok) {
      ready.textContent = "READY";
      ready.classList.add("ok");
      statusText.textContent = "The pinned SETU release is ready.";
    } else {
      statusText.textContent = "The model is warming up. This can take a minute after sleep.";
    }
  } catch {
    statusText.textContent = "The service is still starting.";
  }
}

function render(payload) {
  result.classList.remove("empty");
  result.innerHTML = fields.map((field) => {
    const value = payload.result[field] ?? "null";
    return `<div class="field"><span>${field.replaceAll("_", " ")}</span><strong>${value}</strong></div>`;
  }).join("");
  const info = payload.metadata;
  metadata.textContent = `${info.release} · ${info.quantization} · ${info.latency_ms} ms · ${info.request_id}`;
}

analyze.addEventListener("click", async () => {
  analyze.disabled = true;
  statusText.textContent = "Analyzing and validating the structured output…";
  try {
    const response = await fetch("/v1/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: message.value})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || payload.detail || "Request failed");
    render(payload);
    statusText.textContent = "Strict schema validation passed.";
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    analyze.disabled = false;
  }
});

checkReady();
setInterval(checkReady, 10000);

