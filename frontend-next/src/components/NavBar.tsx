import Link from "next/link";

const pillStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "6px 8px",
  background: "var(--color-input-bg)",
  borderRadius: "999px",
  border: "1px solid var(--color-border)",
};

const iconBtn = (active: boolean) =>
  ({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: 40,
    height: 40,
    borderRadius: "50%",
    textDecoration: "none",
    color: "#fff",
    background: active ? "var(--color-primary)" : "transparent",
    border: active ? "none" : "1px solid transparent",
  }) as React.CSSProperties;

export function NavBar({ active }: { active: "home" | "history" | "metrics" }) {
  return (
    <header
      style={{
        background: "var(--color-secondary)",
        color: "#f8f8f8",
        padding: "14px 20px",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-epilogue), sans-serif",
          fontWeight: 700,
          fontSize: "1.05rem",
        }}
      >
        Zomato AI Recommender
      </span>
      <nav style={pillStyle} aria-label="Main">
        <Link href="/" style={iconBtn(active === "home")} title="Home" aria-current={active === "home" ? "page" : undefined}>
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
            <path d="M8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4.5a.5.5 0 0 0 .5-.5v-4h2v4a.5.5 0 0 0 .5.5H14a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293L8.354 1.146zM2.5 14V7.707l5.5-5.5 5.5 5.5V14H10v-4a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5v4H2.5z" />
          </svg>
        </Link>
        <Link
          href="/history"
          style={{
            ...iconBtn(false),
            color: active === "history" ? "var(--color-primary)" : "var(--color-secondary)",
            background: "#fff",
            border: active === "history" ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
          }}
          title="History"
          aria-current={active === "history" ? "page" : undefined}
        >
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
            <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z" />
            <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z" />
          </svg>
        </Link>
        <Link
          href="/metrics"
          style={{
            ...iconBtn(false),
            color: active === "metrics" ? "var(--color-tertiary)" : "var(--color-secondary)",
            background: "#fff",
            border: active === "metrics" ? "2px solid var(--color-tertiary)" : "1px solid var(--color-border)",
          }}
          title="Metrics"
          aria-current={active === "metrics" ? "page" : undefined}
        >
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
            <path d="M4 11H2v3h2v-3zm5-4H7v7h2V7zm5-5v12h-2V2h2zm-2-1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1h-2zM6 7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7zm-5 4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-3z" />
          </svg>
        </Link>
      </nav>
    </header>
  );
}
