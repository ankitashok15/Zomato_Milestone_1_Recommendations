import type { Metadata } from "next";
import { Epilogue, Plus_Jakarta_Sans } from "next/font/google";
import { AppChrome } from "@/components/AppChrome";
import "./globals.css";

const epilogue = Epilogue({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-epilogue",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jakarta",
});

export const metadata: Metadata = {
  title: "Zomato AI Recommender",
  description: "AI-powered restaurant recommendations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${epilogue.variable} ${jakarta.variable}`}>
      <body className={jakarta.className}>
        <AppChrome>
          <main className="page-main">{children}</main>
        </AppChrome>
      </body>
    </html>
  );
}
