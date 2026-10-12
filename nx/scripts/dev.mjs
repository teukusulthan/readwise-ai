import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const isWindows = process.platform === "win32";
// Works whether this runs from the repo root or from nx/.
const root = existsSync(resolve(process.cwd(), "apps"))
  ? process.cwd()
  : resolve(dirname(fileURLToPath(import.meta.url)), "../..");

const services = [
  {
    name: "backend",
    command: "uv",
    args: ["run", "python", "api.py", "--port", "8020"],
    cwd: resolve(root, "apps/backend"),
    env: { ...process.env, LOGURU_LEVEL: "WARNING" },
    readyPattern: /Uvicorn running on/,
    readyMessage: "Backend ready  http://localhost:8020",
  },
  {
    name: "web",
    command: isWindows ? "npm.cmd" : "npm",
    args: ["run", "dev"],
    cwd: resolve(root, "apps/web"),
    env: (() => {
      const e = { ...process.env };
      delete e.NO_COLOR;
      return e;
    })(),
    readyPattern: /Ready in|- Local:\s+http:\/\/localhost:3000/,
    readyMessage: "Web ready      http://localhost:3000",
  },
];

const importantPatterns = [
  /address already in use/i,
  /EADDRINUSE/i,
  /failed/i,
  /error/i,
  /traceback/i,
  /ModuleNotFoundError/i,
];

const noisyErrorPatterns = [/^at /, /^NX\s+/];

const stripAnsi = (value) => value.replace(/\[[0-9;?]*[A-Za-z]/g, "");

const printInfo = () => {
  console.log("");
  console.log("Dev servers");
  console.log("Web      http://localhost:3000");
  console.log("Backend  http://localhost:8020");
  console.log("Swagger  http://localhost:8020/docs");
  console.log("");
  console.log("Starting. Press Ctrl+C to stop.");
  console.log("");
};

const children = [];
const readyServices = new Set();

const handleOutput = (service, chunk) => {
  for (const rawLine of chunk.toString().split(/\r?\n/)) {
    const line = stripAnsi(rawLine).trim();
    if (!line) continue;
    if (noisyErrorPatterns.some((p) => p.test(line))) continue;

    if (service.readyPattern.test(line) && !readyServices.has(service.name)) {
      readyServices.add(service.name);
      console.log(service.readyMessage);
      continue;
    }

    // show all backend output; only filter web to reduce vite noise
    if (service.name === "backend") {
      console.log(`[backend] ${line}`);
    } else if (importantPatterns.some((p) => p.test(line))) {
      console.log(`[${service.name}] ${line}`);
    }
  }
};

const stopAll = () => {
  for (const child of children) {
    if (!child.killed) child.kill("SIGINT");
  }
};

const spawnService = (service) => {
  // On Windows, quote commands with spaces so cmd.exe resolves them correctly
  const cmd =
    isWindows && service.command.includes(" ")
      ? `"${service.command}"`
      : service.command;
  const child = spawn(cmd, service.args, {
    cwd: service.cwd,
    env: service.env,
    shell: isWindows,
    stdio: ["inherit", "pipe", "pipe"],
  });

  children.push(child);

  child.stdout.on("data", (chunk) => handleOutput(service, chunk));
  child.stderr.on("data", (chunk) => handleOutput(service, chunk));

  child.on("error", (err) => {
    console.log(`[${service.name}] Failed to start: ${err.message}`);
    stopAll();
  });

  child.on("exit", (code, signal) => {
    if (signal === "SIGINT") return;
    if (code === 130) return;
    if (code && code !== 0) {
      console.log(`[${service.name}] exited with code ${code}`);
      stopAll();
    }
  });
};

printInfo();

for (const service of services) {
  spawnService(service);
}

process.on("SIGINT", () => {
  console.log("\nStopping dev servers...");
  stopAll();
});
