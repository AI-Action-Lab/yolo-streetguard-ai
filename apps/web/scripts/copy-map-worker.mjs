import { copyFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(root, "node_modules", "maplibre-gl", "dist", "maplibre-gl-worker.mjs");
const destination = join(root, "public", "maplibre-gl-worker.mjs");

await mkdir(dirname(destination), { recursive: true });
await copyFile(source, destination);
