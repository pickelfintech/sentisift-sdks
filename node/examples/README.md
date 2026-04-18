# Examples - Node SDK

Runnable examples for common integration patterns. Each script is self-contained: set `SENTISIFT_API_KEY` in your environment and run with Node 18+.

```bash
npm install @sentisift/client
export SENTISIFT_API_KEY=sk_sentisift_your_key_here
node examples/quickstart.mjs
```

| File | What it demonstrates |
|---|---|
| `quickstart.mjs` | The minimal happy path: send three comments, print the result, print balance. |
| `error_handling.mjs` | All the typed exceptions in one place. Shows how to read `docsUrl` and `requestId` for self-service debugging. |
| `wait_for_ready.mjs` | Poll `/health` and use `waitUntilReady()` to gate on cold-start model loading after a deploy. |
| `express_middleware.mjs` | Drop-in Express middleware that calls `/analyze` after a comment is saved and returns the moderated batch to the client. |

For more deployment patterns (FastAPI, Flask, WordPress, Cloudflare Worker), see the **Integration Recipes** section of [api-docs.html](https://sentisift.com/api-docs.html).

> Why `.mjs`? These examples use ES module syntax (`import`) so you can paste them into any modern Node project without configuration. If your project is CommonJS, swap the imports to `const { SentiSift } = require("@sentisift/client")`.
