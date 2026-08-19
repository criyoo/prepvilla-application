import type { Metadata } from "next";
import { AboutPage } from "../ui/about/AboutPage";

export const metadata: Metadata = {
  title: "About PrepVilla",
  description: "Learn how PrepVilla helps students find trusted tutors and helps teachers build better learning experiences.",
};

export default function Page() {
  return <AboutPage />;
}
