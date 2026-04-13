"use client";

import { Button } from "./Button";

type Props = { streamlitUrl: string };

export function StreamlitConnectHome({ streamlitUrl }: Props) {
  const openApp = () => {
    window.open(streamlitUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <>
      <div className="divider-trio" aria-hidden>
        <span />
        <span />
        <span />
      </div>

      <section className="card">
        <h1>Find restaurants</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          This deployment uses your <strong>Streamlit</strong> app for recommendations (localities, cuisines, Groq ranking).
          Streamlit does not expose the same JSON API as FastAPI, so the form below is replaced with a direct link to your
          live app.
        </p>
        <div className="row-actions">
          <Button type="button" variant="primary" onClick={openApp}>
            Open recommender (Streamlit)
          </Button>
          <Button
            type="button"
            variant="outlined"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(streamlitUrl);
              } catch {
                /* ignore */
              }
            }}
          >
            Copy Streamlit URL
          </Button>
        </div>
        <p className="field-hint" style={{ marginTop: 12 }}>
          URL:{" "}
          <a href={streamlitUrl} target="_blank" rel="noopener noreferrer">
            {streamlitUrl}
          </a>
        </p>
      </section>

      <section className="card">
        <h2 className="heading">Optional: Next.js form + metrics</h2>
        <p className="muted">
          To use the full form on this site (localities, metrics, history sync with API), deploy{" "}
          <strong>FastAPI</strong> (<code>phase6</code>) somewhere, set <code>BACKEND_URL</code> on Vercel to that HTTPS
          origin, and set <code>NEXT_PUBLIC_BACKEND_MODE=fastapi</code> (or remove it). See README.
        </p>
      </section>
    </>
  );
}
