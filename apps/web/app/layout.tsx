import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoScout — Find the right car",
  description:
    "Search real vehicle listings with a simple description of what you need.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
