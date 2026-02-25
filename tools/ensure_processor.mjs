import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outBin = path.join(root, "build", "bin", "video_dedupe_processor");

function buildMacArm64() {
  const script = path.join(root, "tools", "build_processor_macos_arm64.sh");
  const res = spawnSync("bash", [script], { stdio: "inherit" });
  if (res.status !== 0) process.exit(res.status ?? 1);
}

// For the current primary target, only enforce on Apple Silicon macOS.
if (process.platform === "darwin" && process.arch === "arm64") {
  if (!fs.existsSync(outBin)) {
    buildMacArm64();
  }
}
