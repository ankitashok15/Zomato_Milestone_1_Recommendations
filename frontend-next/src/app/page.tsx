import { HomePage } from "@/components/HomePage";
import { StreamlitConnectHome } from "@/components/StreamlitConnectHome";
import { BACKEND_MODE, STREAMLIT_APP_URL } from "@/lib/runtimeConfig";

function StreamlitConfigMissing() {
  return (
    <>
      <div className="divider-trio" aria-hidden>
        <span />
        <span />
        <span />
      </div>
      <section className="card">
        <h1>Configuration needed</h1>
        <p className="status-msg error">
          <code>NEXT_PUBLIC_BACKEND_MODE</code> is <code>streamlit</code> but <code>NEXT_PUBLIC_STREAMLIT_APP_URL</code>{" "}
          is missing. Add it in Vercel → Settings → Environment Variables (e.g.{" "}
          <code>https://zomatorecommendations.streamlit.app</code>), then redeploy.
        </p>
      </section>
    </>
  );
}

export default function Page() {
  if (BACKEND_MODE === "streamlit") {
    if (!STREAMLIT_APP_URL) return <StreamlitConfigMissing />;
    return <StreamlitConnectHome streamlitUrl={STREAMLIT_APP_URL} />;
  }
  return <HomePage />;
}
