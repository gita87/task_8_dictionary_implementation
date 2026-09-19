const form = document.querySelector("#convert-form");
const input = document.querySelector("#document");
const button = document.querySelector("#file-button");
const message = document.querySelector("#message");

function filenameFromDisposition(header) {
  const utf8 = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8) return decodeURIComponent(utf8[1]);
  const basic = header.match(/filename="?([^";]+)"?/i);
  return basic ? basic[1] : "dictionary.csv";
}

function setState(text, type = "") {
  message.textContent = text;
  message.className = `message ${type}`.trim();
}

async function convertSelectedFile() {
  if (!input.files.length) return;

  const payload = new FormData(form);
  input.disabled = true;
  button.disabled = true;
  button.textContent = "Converting...";
  setState(input.files[0].name);

  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: payload,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = typeof body.error === "object" ? body.error.message : body.error;
      throw new Error(detail || "Conversion failed. Please check the document.");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filenameFromDisposition(response.headers.get("Content-Disposition") || "");
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    const rows = response.headers.get("X-Row-Count") || "0";
    setState(`Done. ${rows} rows converted.`, "success");
  } catch (error) {
    setState(error.message, "error");
  } finally {
    input.disabled = false;
    input.value = "";
    button.disabled = false;
    button.textContent = "Choose DOCX and convert";
  }
}

button.addEventListener("click", () => input.click());
input.addEventListener("change", convertSelectedFile);
