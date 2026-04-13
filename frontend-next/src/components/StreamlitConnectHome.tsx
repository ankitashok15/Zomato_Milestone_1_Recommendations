"use client";

import { Button } from "./Button";

type Props = { streamlitUrl: string };

/**
 * Single-page shell: Next.js chrome (nav, design system) + embedded Streamlit (Python recommender).
 * If Streamlit sets X-Frame-Options, the iframe may be blank — use “Open in new tab”.
 */
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

      <section className="card streamlit-unified-toolbar">
        <div className="streamlit-unified-toolbar-inner">
          <div>
            <h1 style={{ marginBottom: 4 }}>Find restaurants</h1>
            <p className="muted" style={{ margin: 0 }}>
              <strong>Next.js</strong> (this site) + <strong>Streamlit</strong> (embedded below) — one page to try both.
            </p>
          </div>
          <div className="row-actions" style={{ marginTop: 0 }}>
            <Button type="button" variant="primary" onClick={openApp}>
              Open Streamlit in new tab
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
        </div>
        <p className="field-hint" style={{ marginTop: 10, marginBottom: 0 }}>
          If the frame stays empty, Streamlit Cloud may block embedding — use the button above. Full Next form + metrics
          need a deployed FastAPI <code>BACKEND_URL</code> and <code>NEXT_PUBLIC_BACKEND_MODE=fastapi</code>.
        </p>
      </section>

      <div className="streamlit-unified-frame-wrap">
        <iframe
          title="Streamlit recommender (Python backend)"
          src={streamlitUrl}
          className="streamlit-unified-frame"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>
    </>
  );
}
