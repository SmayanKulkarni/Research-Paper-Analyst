import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { BackgroundOrbs } from "@/components/ui/BackgroundOrbs";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata = {
  title: "Research Paper Analyst | AI-Powered Paper Analysis",
  description:
    "Analyze research papers with AI agents. Get feedback on grammar, structure, citations, and consistency.",
  keywords: [
    "research paper",
    "AI analysis",
    "academic writing",
    "proofreading",
    "citation check",
  ],
  openGraph: {
    title: "Research Paper Analyst",
    description: "AI-Powered Research Paper Analysis",
    type: "website",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrainsMono.variable}`}>
        <BackgroundOrbs />
        {children}
      </body>
    </html>
  );
}
