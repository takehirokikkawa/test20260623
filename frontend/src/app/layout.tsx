import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/Toast";

export const metadata: Metadata = {
  title: "TechInsight — AI Knowledge Base",
  description:
    "TechInsight: search and manage technical articles with hybrid AI-powered search.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
