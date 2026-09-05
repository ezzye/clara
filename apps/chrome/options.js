const fields = ["endpoint", "origins"];
chrome.storage.local
  .get(fields)
  .then((data) =>
    fields.forEach((f) => (document.getElementById(f).value = data[f] || "")),
  );
document.getElementById("save").onclick = async () => {
  try {
    const endpoint = new URL(document.getElementById("endpoint").value);
    if (
      endpoint.protocol !== "https:" ||
      endpoint.pathname !== "/" ||
      endpoint.search ||
      endpoint.hash
    )
      throw Error("Use the HTTPS app origin only.");
    const origins = document.getElementById("origins").value.trim();
    const list = origins
      .split("\n")
      .filter(Boolean)
      .map((s) => {
        const u = new URL(s.trim());
        if (u.protocol !== "https:" || u.pathname !== "/" || u.search || u.hash)
          throw Error("Use exact HTTPS origins.");
        return u.origin;
      });
    const token = document.getElementById("token").value;
    if (!token) throw Error("Enter a fresh upload-only key.");
    const granted = await chrome.permissions.request({
      origins: [endpoint.origin + "/*"],
    });
    if (!granted) throw Error("Connection permission declined.");
    await chrome.storage.local.set({
      endpoint: endpoint.origin,
      origins: list.join("\n"),
      token,
    });
    document.getElementById("token").value = "";
    document.getElementById("status").textContent =
      "Saved. Open a permitted work page and use the Clara button to preview a brief.";
  } catch (e) {
    document.getElementById("status").textContent = e.message;
  }
};
