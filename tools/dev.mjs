import net from "node:net";
import { spawn } from "node:child_process";

const BASE_PORT = 5173;
const HOST = "localhost";

function canListen(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.on("error", () => resolve(false));
    server.listen({ port, host: HOST }, () => {
      server.close(() => resolve(true));
    });
  });
}

async function findOpenPort(startPort) {
  for (let p = startPort; p < startPort + 50; p += 1) {
    // eslint-disable-next-line no-await-in-loop
    const ok = await canListen(p);
    if (ok) return p;
  }
  throw new Error(`No open port found in range ${startPort}-${startPort + 49}`);
}

async function waitForHttpOk(url, timeoutMs = 20000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      // Node 18+ has global fetch.
      // Vite responds with 200 for "/".
      // eslint-disable-next-line no-undef
      const res = await fetch(url, { method: "GET" });
      if (res.ok) return true;
    } catch {
      // ignore
    }
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 250));
  }
  return false;
}

function npmCmd() {
  // Windows uses npm.cmd; spawn with shell false needs correct executable.
  return process.platform === "win32" ? "npm.cmd" : "npm";
}

function spawnLogged(name, cmd, args, env) {
  const child = spawn(cmd, args, {
    env,
    stdio: "inherit"
  });
  child.on("exit", (code, signal) => {
    const suffix = signal ? `signal ${signal}` : `code ${code}`;
    // Keep the message short; this is a dev helper.
    // eslint-disable-next-line no-console
    console.log(`[dev] ${name} exited (${suffix})`);
  });
  return child;
}

async function main() {
  const port = await findOpenPort(BASE_PORT);
  const devUrl = `http://${HOST}:${port}`;

  // eslint-disable-next-line no-console
  console.log(`[dev] Starting Vite at ${devUrl}`);

  const env = {
    ...process.env
  };

  const vite = spawnLogged(
    "vite",
    npmCmd(),
    ["exec", "--", "vite", "--port", String(port), "--host", HOST],
    env
  );

  const ok = await waitForHttpOk(`${devUrl}/`);
  if (!ok) {
    vite.kill("SIGTERM");
    throw new Error(`[dev] Vite did not become ready at ${devUrl} within timeout`);
  }

  // eslint-disable-next-line no-console
  console.log(`[dev] Starting Electron with VITE_DEV_SERVER_URL=${devUrl}`);

  const electronEnv = {
    ...env,
    VITE_DEV_SERVER_URL: devUrl,
    ELECTRON_ENABLE_LOGGING: "1"
  };

  const electron = spawnLogged("electron", npmCmd(), ["exec", "--", "electron", "."], electronEnv);

  const shutdown = () => {
    try {
      electron.kill("SIGTERM");
    } catch {
      // ignore
    }
    try {
      vite.kill("SIGTERM");
    } catch {
      // ignore
    }
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);

  // If either process exits, shut down the other.
  electron.on("exit", () => shutdown());
  vite.on("exit", () => shutdown());
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(String(err?.stack || err));
  process.exitCode = 1;
});

