import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Footer } from "./ui/shared/Footer";

export const metadata: Metadata = {
  title: "PrepVilla — Find Verified Teachers",
  description: "Search verified tutors by subject, price, and availability.",
};

export const viewport: Viewport = {
  themeColor: "#223319",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
        <Footer />
      </body>
    </html>
  );
}
