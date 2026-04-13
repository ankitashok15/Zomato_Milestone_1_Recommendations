"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import { NavBar } from "./NavBar";

function NavBarWithPath() {
  const path = usePathname();
  const active = path.startsWith("/history") ? "history" : path.startsWith("/metrics") ? "metrics" : "home";
  return <NavBar active={active} />;
}

export function AppChrome({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Suspense fallback={<header className="site-header-skeleton" aria-hidden />}>
        <NavBarWithPath />
      </Suspense>
      {children}
    </>
  );
}
