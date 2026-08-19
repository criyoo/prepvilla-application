import type { Metadata } from "next";
import { HowItWorksPage } from "../ui/how-it-works/HowItWorksPage";

export const metadata: Metadata = {
  title: "How PrepVilla Works for Students and Tutors",
  description: "See how students find and book tutors, and how tutors build verified profiles, teach lessons, and receive payouts on PrepVilla.",
};

export default function Page() {
  return <HowItWorksPage />;
}
