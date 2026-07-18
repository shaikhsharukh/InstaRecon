import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InstaRecon",
  description: "Instant company intelligence — paste a URL, see investigation results.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col" style={{ fontFamily: "'Geist', 'Inter', Arial, Helvetica, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
