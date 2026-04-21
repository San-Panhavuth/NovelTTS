import type { NextConfig } from "next";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

function loadRootEnvFile(filePath: string) {
  if (!existsSync(filePath)) {
    return;
  }

  const lines = readFileSync(filePath, "utf-8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const sepIndex = trimmed.indexOf("=");
    if (sepIndex <= 0) {
      continue;
    }

    const key = trimmed.slice(0, sepIndex).trim();
    const rawValue = trimmed.slice(sepIndex + 1).trim();
    const value = rawValue.replace(/^['"]|['"]$/g, "");

    if (!process.env[key]) {
      process.env[key] = value;
    }
  }
}

const workspaceRoot = path.resolve(process.cwd(), "..");
loadRootEnvFile(path.join(workspaceRoot, ".env.local"));
loadRootEnvFile(path.join(workspaceRoot, ".env"));

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  experimental: {
    serverActions: {
      bodySizeLimit: "50mb",
    },
  },
};

export default nextConfig;
