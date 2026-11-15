// Fails early with a clear message when the Python environment for the API is missing.
import { existsSync } from "node:fs";

if (!existsSync(new URL("../../.venv/bin/python", import.meta.url))) {
  console.error(
    "Python environment not found. From the project root run:\n" +
      "  python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements.lock && .venv/bin/python -m pip install -e . --no-deps",
  );
  process.exit(1);
}
