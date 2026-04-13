import { HomePage } from "@/components/HomePage";
import { StreamlitConnectHome } from "@/components/StreamlitConnectHome";
import { BACKEND_MODE, STREAMLIT_APP_URL } from "@/lib/runtimeConfig";

export default function Page() {
  if (BACKEND_MODE === "streamlit" && STREAMLIT_APP_URL) {
    return <StreamlitConnectHome streamlitUrl={STREAMLIT_APP_URL} />;
  }
  return <HomePage />;
}
