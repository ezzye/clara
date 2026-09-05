chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (sender.id !== chrome.runtime.id || message.type !== "sendBrief")
    return false;
  (async () => {
    try {
      const { endpoint, token } = await chrome.storage.local.get([
        "endpoint",
        "token",
      ]);
      if (!endpoint?.startsWith("https://") || !token)
        throw Error("Set up the private connection first.");
      const res = await fetch(endpoint + "/api/ingest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + token,
        },
        body: JSON.stringify({
          evidence: [
            {
              id: crypto.randomUUID(),
              source: "chrome",
              summary: String(message.summary).slice(0, 800),
              observedAt: new Date().toISOString(),
              confidence: "low",
            },
          ],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.error || "Could not connect");
      if (data.paused) throw Error("Clara is paused. Nothing was collected.");
      reply({ ok: true });
    } catch (e) {
      reply({ ok: false, error: e.message });
    }
  })();
  return true;
});
