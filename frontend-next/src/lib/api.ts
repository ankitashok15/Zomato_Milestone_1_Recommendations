const API_PREFIX = "/api/backend";

const REQUEST_MS = 15_000;

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

async function parseJsonOrExplain<T>(res: Response): Promise<T> {
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const body = await readErrorBody(res);
    const looksLikeHtml = /<!doctype html>|<html/i.test(body);
    if (looksLikeHtml) {
      throw new Error(
        "Backend returned HTML instead of API JSON. On Vercel, set NEXT_PUBLIC_BACKEND_MODE=streamlit and NEXT_PUBLIC_STREAMLIT_APP_URL for Streamlit deployments."
      );
    }
    throw new Error("Unexpected backend response format. Expected JSON API response.");
  }
  return res.json() as Promise<T>;
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
  return parseJsonOrExplain<T>(res);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_PREFIX}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
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
  return parseJsonOrExplain<T>(res);
}
