const API_PREFIX = "/api/backend";

const REQUEST_MS = 25_000;

function requestTimeoutSignal(): AbortSignal | undefined {
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(REQUEST_MS);
  }
  return undefined;
}

async function readErrorBody(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = `${API_PREFIX}${path}`;
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store", signal: requestTimeoutSignal() });
  } catch (e) {
    const name = e instanceof Error ? e.name : "";
    if (name === "TimeoutError" || name === "AbortError") {
      throw new Error(
        `Request timed out after ${REQUEST_MS / 1000}s. Is the API running and BACKEND_URL correct?`
      );
    }
    throw e instanceof Error ? e : new Error(String(e));
  }
  if (!res.ok) throw new Error(await readErrorBody(res));
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_PREFIX}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: requestTimeoutSignal(),
    });
  } catch (e) {
    const name = e instanceof Error ? e.name : "";
    if (name === "TimeoutError" || name === "AbortError") {
      throw new Error(
        `Request timed out after ${REQUEST_MS / 1000}s. Is the API running and BACKEND_URL correct?`
      );
    }
    throw e instanceof Error ? e : new Error(String(e));
  }
  if (!res.ok) throw new Error(await readErrorBody(res));
  return res.json() as Promise<T>;
}
