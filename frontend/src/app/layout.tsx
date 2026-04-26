import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "NewsIntel — Global News Intelligence",
  description: "Real-time global news crawling, analysis, and intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0B0B0B] text-white antialiased`}>
        <Sidebar />
        <main className="ml-60 min-h-screen flex flex-col">{children}</main>
      </body>
    </html>
  );
}
