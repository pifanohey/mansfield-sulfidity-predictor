import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import TopNav from "@/components/layout/TopNav";
import Providers from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Sulfidity Predictor",
  description: "Kraft Mill Sulfidity Predictor - Pine Hill Mill",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrains.variable} font-sans antialiased`}
      >
        <Providers>
          <div className="flex h-screen flex-col">
            <TopNav />
            <div className="flex flex-1 flex-col overflow-hidden">
              {children}
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
