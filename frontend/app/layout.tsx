import type { Metadata } from "next";
import "./globals.css";
import KeepAlive from "./components/KeepAlive";

export const metadata: Metadata = {
  title: "AI Visibility Optimization Platform (AIVOP)",
  description: "Identify and optimize your brand discoverability inside modern AI recommendation systems like ChatGPT, Gemini, and Claude.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <KeepAlive />
        {children}
      </body>
    </html>
  );
}
