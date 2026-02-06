import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

export async function groupDuplicates(files, strategyKey) {
  if (!Array.isArray(files) || files.length === 0) {
    return { total: 0, duplicateGroups: [] };
  }

  const signatures = new Map();

  for (const filePath of files) {
    const signature = await computeSignature(filePath, strategyKey);
    if (!signatures.has(signature)) signatures.set(signature, []);
    signatures.get(signature).push(filePath);
  }

  const groups = [];
  for (const [signature, group] of signatures.entries()) {
    if (group.length > 1) {
      groups.push({
        signature,
        keep: group[0],
        duplicates: group.slice(1)
      });
    }
  }

  return { total: files.length, duplicateGroups: groups };
}

export async function computeSignature(filePath, strategyKey) {
  switch (strategyKey) {
    case "size-bytes":
      return String((await fs.promises.stat(filePath)).size);
    case "name-only":
      return path.basename(filePath).toLowerCase();
    case "hash-md5":
    default:
      return hashFile(filePath);
  }
}

async function hashFile(filePath) {
  return new Promise((resolve, reject) => {
    const hash = createHash("md5");
    const stream = fs.createReadStream(filePath);
    stream.on("error", reject);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("end", () => resolve(hash.digest("hex")));
  });
}
