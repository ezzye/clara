export type Task = {
  id: string;
  title: string;
  category: string;
  minutes: number;
  priority: number;
  nextStep: string;
  doneWhen: string;
  projectId: string;
  lifeArea?: string;
  due: string;
  status: string;
  source: string;
};
export type Block = {
  id: string;
  date: string;
  start: number;
  minutes: number;
  title: string;
  kind: string;
  locked: boolean;
  status: string;
  taskId?: string;
  eventId?: string;
  reason: string;
  startedAt?: string;
  actualMinutes?: number;
};
export type Meeting = {
  id: string;
  date: string;
  start: number;
  minutes: number;
  title: string;
  prepMinutes: number;
  notes: string;
  source: string;
  confirmed: boolean;
};
export type State = {
  revision: number;
  tasks: Task[];
  plan: Block[];
  events: Meeting[];
  projects: {
    id: string;
    title: string;
    outcome: string;
    nextStep: string;
    source: string;
  }[];
  goals: {
    id: string;
    title: string;
    outcome: string;
    horizon: string;
    due: string;
    status: string;
  }[];
  evidence: {
    id: string;
    source: string;
    summary: string;
    observedAt: string;
    confidence: string;
    status: string;
  }[];
  devices: {
    id: string;
    name: string;
    os: string;
    lastSeen: string | null;
    revoked: boolean;
  }[];
  settings: {
    paused: boolean;
    energy: string;
    focusMinutes: number;
    dayStart: number;
    dayEnd: number;
    bufferMinutes: number;
    maxPriorities: number;
  };
  planner: { mode: string; message: string; lastRun: string | null };
};
export type Config = { mode: string; clientId?: string; domain?: string };
export let config: Config = { mode: "local" };
export async function api(path: string, body?: unknown) {
  const token = sessionStorage.getItem("clara-access");
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await res.json();
  if (!res.ok)
    throw new Error(data.error || `Sign-in required (${res.status})`);
  return data;
}
const base64 = (b: Uint8Array) =>
  btoa(String.fromCharCode(...b))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
export async function initialize() {
  config = await api("/config");
  const hash = new URLSearchParams(location.hash.slice(1));
  if (hash.has("launch")) {
    await api("/api/bootstrap", { token: hash.get("launch") });
    history.replaceState(null, "", location.pathname);
  }
  const params = new URLSearchParams(location.search);
  if (params.has("code")) {
    const expected = sessionStorage.getItem("clara-oauth-state");
    const verifier = sessionStorage.getItem("clara-pkce");
    if (!expected || params.get("state") !== expected || !verifier)
      throw new Error("Sign-in could not be verified. Please start again.");
    const response = await fetch(`${config.domain}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: config.clientId!,
        code: params.get("code")!,
        redirect_uri: location.origin + "/",
        code_verifier: verifier,
      }),
    });
    const data = await response.json();
    history.replaceState(null, "", "/");
    sessionStorage.removeItem("clara-pkce");
    sessionStorage.removeItem("clara-oauth-state");
    if (!response.ok || !data.access_token)
      throw new Error("Sign-in expired. Please try again.");
    sessionStorage.setItem("clara-access", data.access_token);
  }
  return api("/api/state") as Promise<State>;
}
export async function signIn() {
  const verifier = base64(crypto.getRandomValues(new Uint8Array(48)));
  const state = base64(crypto.getRandomValues(new Uint8Array(24)));
  const challenge = base64(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)),
    ),
  );
  sessionStorage.setItem("clara-pkce", verifier);
  sessionStorage.setItem("clara-oauth-state", state);
  location.href =
    `${config.domain}/oauth2/authorize?` +
    new URLSearchParams({
      client_id: config.clientId!,
      response_type: "code",
      scope: "openid email",
      redirect_uri: location.origin + "/",
      state,
      code_challenge: challenge,
      code_challenge_method: "S256",
    });
}
export function signOut() {
  sessionStorage.removeItem("clara-access");
  if (config.mode === "aws")
    location.href =
      `${config.domain}/logout?` +
      new URLSearchParams({
        client_id: config.clientId!,
        logout_uri: location.origin + "/",
      });
  else location.reload();
}
