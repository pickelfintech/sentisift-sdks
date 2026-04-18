// Minimal SentiSift quickstart for Node.
//
// Prerequisites:
//   npm install @sentisift/client
//   export SENTISIFT_API_KEY=sk_sentisift_your_key_here
//
// Run:
//   node quickstart.mjs

import { SentiSift } from "@sentisift/client";

const client = new SentiSift(); // reads SENTISIFT_API_KEY from env

const result = await client.analyze({
  articleUrl: "https://example.com/article/quickstart",
  articleText: "The article body. Send this on the FIRST batch only.",
  title: "Quickstart Article",
  comments: [
    { text: "Great points, well argued.", author: "alice", time: "2026-04-18T10:00:00", likes: 12 },
    { text: "I disagree, here's why...", author: "bob", time: "2026-04-18T10:05:00", likes: 3, dislikes: 1 },
    { text: "Buy crypto-coin-x at 10x leverage now!", author: "user_29481", time: "2026-04-18T10:07:00" },
  ],
});

if (result.status === "buffered") {
  console.log(`Buffered: ${result.buffered_count}/${result.threshold} comments not yet analyzed.`);
  console.log("Send more batches for this article and the buffer will eventually flip to 'processed'.");
} else {
  console.log(`Processed ${result.comments.length} comments:\n`);
  for (const c of result.comments) {
    const tag = c.is_influence ? " [SentiSift]" : "";
    console.log(`  [${c.sentiment_label.padEnd(10)}] ${c.text}${tag}`);
  }
  console.log(`\nModeration: ${result.moderation.total_approved} approved, ${result.moderation.total_removed} removed.`);
  console.log(`Balance after this call: ${result.comment_balance} comments remaining.`);
}

const usage = await client.getUsage();
console.log(`\nLifetime balance: ${usage.comment_balance} comments.`);
