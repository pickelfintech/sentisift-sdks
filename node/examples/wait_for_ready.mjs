// Wait for the SentiSift service to be ready before sending traffic.
//
// Useful right after an API service deploy. Models take 10-60 seconds to
// load. `waitUntilReady()` polls /health and returns when the service
// reports `status: "ready"`, or throws if the timeout is exceeded.
//
// Prerequisites:
//   npm install @sentisift/client
//   export SENTISIFT_API_KEY=sk_sentisift_your_key_here

import { SentiSift } from "@sentisift/client";

const client = new SentiSift();

const health = await client.getHealth();
console.log(`Initial state: ${health.status}`);
if (health.progress) {
  console.log(`  Progress: ${health.progress.current}/${health.progress.total} (${health.progress.scorer_name})`);
}

if (health.status !== "ready") {
  console.log("Waiting up to 60s for service to become ready...");
  await client.waitUntilReady({ timeoutMs: 60_000 });
  console.log("Service is ready.");
} else {
  console.log("Service was already ready. No wait needed.");
}

// Now safe to call analyze, getUsage, etc.
const usage = await client.getUsage();
console.log(`Balance: ${usage.comment_balance} comments.`);
