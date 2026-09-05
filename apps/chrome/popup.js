let source = "";
const status = document.getElementById("status");
document.getElementById("settings").onclick = () =>
  chrome.runtime.openOptionsPage();
document.getElementById("preview").onclick = async () => {
  try {
    const config = await chrome.storage.local.get(["origins"]);
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    const url = new URL(tab.url);
    if (!config.origins?.split("\n").includes(url.origin))
      throw Error("This work origin is not on your approved list.");
    const result = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        title: document.title,
        text: (document.querySelector("main") || document.body).innerText.slice(
          0,
          6000,
        ),
      }),
    });
    const data = result[0].result;
    if (
      /one.time|passcode|password|verification code|secure key|\botp\b|api.?key|bearer/i.test(
        data.text,
      )
    )
      throw Error(
        "Authentication material detected. Capture a different page.",
      );
    source = url.hostname;
    document.getElementById("brief").value = (
      data.title +
      "\n" +
      data.text
    ).slice(0, 800);
    document.getElementById("send").disabled = false;
    status.textContent =
      "Review this extract before sending. Nothing sent yet.";
  } catch (e) {
    status.textContent = e.message;
  }
};
document.getElementById("send").onclick = async () => {
  const summary = document.getElementById("brief").value;
  if (!summary) return;
  const reply = await chrome.runtime.sendMessage({
    type: "sendBrief",
    summary: "Work page (" + source + "): " + summary,
  });
  status.textContent = reply.ok ? "Saved as unreviewed evidence." : reply.error;
};
