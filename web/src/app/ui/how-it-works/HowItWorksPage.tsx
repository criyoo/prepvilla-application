"use client";

import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  Banknote,
  BookOpenCheck,
  CalendarCheck2,
  CheckCircle2,
  CircleDollarSign,
  GraduationCap,
  MessageCircle,
  Search,
  ShieldCheck,
  Star,
  UserRoundCheck,
  UsersRound,
  Video,
  WalletCards,
} from "lucide-react";
import { useState, type ComponentType } from "react";
import { AppHeader } from "../shared/AppHeader";
import { Button } from "../shared/Button";

type Audience = "student" | "tutor";
type Step = {
  title: string;
  description: string;
  details: string[];
  icon: ComponentType<{ className?: string }>;
};

const journeys: Record<Audience, {
  label: string;
  title: string;
  description: string;
  highlights: string[];
  steps: Step[];
  ctaLabel: string;
  ctaHref: string;
}> = {
  student: {
    label: "For students",
    title: "Find the right tutor and keep every lesson on track.",
    description: "PrepVilla gives you a clear route from finding a tutor to booking, learning, paying securely, and building lasting progress.",
    highlights: ["Compare tutor profiles", "Book and pay securely", "Learn online or in person"],
    ctaLabel: "Find a tutor",
    ctaHref: "/search",
    steps: [
      {
        title: "Create your student account",
        description: "Start with the basics so your learning activity stays organised in one secure place.",
        details: [
          "Sign up manually or continue with Google",
          "Confirm your account details and complete your profile",
          "Use your dashboard to manage bookings, messages, favourites, and billing",
        ],
        icon: UserRoundCheck,
      },
      {
        title: "Discover tutors who fit",
        description: "Search beyond a name and compare the details that matter for your learning goals.",
        details: [
          "Filter by subject, location, language, price, and lesson format",
          "Review experience, qualifications, availability, and verification details",
          "Save promising tutors to your favourites for easy comparison",
        ],
        icon: Search,
      },
      {
        title: "Connect and choose confidently",
        description: "Ask questions before committing and make sure the tutor is right for you.",
        details: [
          "Message tutors directly through PrepVilla",
          "Discuss your goals, preferred schedule, level, and lesson format",
          "Keep important conversations together with your account records",
        ],
        icon: MessageCircle,
      },
      {
        title: "Request and pay for a lesson",
        description: "Choose the lesson details, send your request, and follow its status from your dashboard.",
        details: [
          "Select an available time and online or face-to-face delivery",
          "Review the booking and payment details before confirming",
          "Pay securely through Flutterwave using an available payment method",
        ],
        icon: CalendarCheck2,
      },
      {
        title: "Learn in the agreed format",
        description: "Attend the lesson online or meet at the agreed location for an in-person session.",
        details: [
          "Open eligible online lessons from the video room",
          "Use messages to stay aligned if plans or lesson details change",
          "Keep upcoming and completed lessons visible in Bookings",
        ],
        icon: Video,
      },
      {
        title: "Confirm completion and keep progressing",
        description: "Confirm when the lesson is complete so the tutor payment can move to the next stage.",
        details: [
          "Check that the lesson was delivered as agreed",
          "Confirm completion from the booking record",
          "Share helpful feedback and book another lesson when you are ready",
        ],
        icon: CheckCircle2,
      },
    ],
  },
  tutor: {
    label: "For tutors",
    title: "Build a trusted teaching profile and grow your tutoring work.",
    description: "PrepVilla brings verification, discovery, bookings, lessons, and payouts into one practical teaching journey.",
    highlights: ["Build a verified profile", "Control your availability", "Receive protected payouts"],
    ctaLabel: "Become a tutor",
    ctaHref: "/signup/tutor",
    steps: [
      {
        title: "Create your tutor account",
        description: "Join PrepVilla as a tutor and set up the account you will use to manage your teaching work.",
        details: [
          "Sign up manually or continue with Google",
          "Add your personal, contact, and teaching information",
          "Use the tutor dashboard to manage your profile and activity",
        ],
        icon: GraduationCap,
      },
      {
        title: "Complete tutor verification",
        description: "Submit the information needed to help students understand who they are learning with.",
        details: [
          "Provide identity, qualification, experience, and residence details",
          "Upload the requested supporting documents and profile media",
          "Follow the verification status and respond if more information is requested",
        ],
        icon: ShieldCheck,
      },
      {
        title: "Build a profile students can trust",
        description: "Present your subjects, approach, rates, and experience clearly to the right learners.",
        details: [
          "Choose the subjects, levels, languages, and lesson formats you support",
          "Set your hourly rate and explain how you help students learn",
          "Keep your profile accurate so students can make informed choices",
        ],
        icon: BadgeCheck,
      },
      {
        title: "Set availability and respond",
        description: "Stay in control of when you teach and which lesson requests you accept.",
        details: [
          "Add and maintain available teaching times",
          "Discuss student goals and lesson details through secure messaging",
          "Review each booking request before accepting it",
        ],
        icon: CalendarCheck2,
      },
      {
        title: "Deliver a great lesson",
        description: "Teach online or face-to-face using the format agreed with the student.",
        details: [
          "Prepare around the subject, level, and goals in the booking",
          "Use the video room for eligible online sessions",
          "Keep communication and lesson status up to date",
        ],
        icon: BookOpenCheck,
      },
      {
        title: "Confirm completion and receive your payout",
        description: "Payment is protected while the lesson is pending and released after completion is confirmed.",
        details: [
          "Confirm that the agreed lesson has been delivered",
          "The student also confirms completion before payout release",
          "PrepVilla retains a 5% platform fee and 95% is paid to your registered bank account",
        ],
        icon: Banknote,
      },
    ],
  },
};

const sharedBenefits = [
  { title: "Verified participation", description: "Tutor verification and clearer profiles help students make better-informed choices.", icon: ShieldCheck },
  { title: "Connected records", description: "Bookings, messages, payments, lesson status, and support requests stay connected to your account.", icon: WalletCards },
  { title: "Direct communication", description: "Students and tutors can discuss goals, availability, and lesson details without unnecessary intermediaries.", icon: MessageCircle },
  { title: "Flexible learning", description: "Choose online or face-to-face lessons where the tutor offers that delivery option.", icon: UsersRound },
];

export function HowItWorksPage() {
  const [audience, setAudience] = useState<Audience>("student");
  const journey = journeys[audience];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader overlay />

      <main className="hero-under-header">
        <section className="relative overflow-hidden border-b border-black/8 bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-navy)_62%,var(--palette-plum)_100%)] text-white">
          <div className="pointer-events-none absolute -right-28 -top-36 h-96 w-96 rounded-full bg-accent/30 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-44 left-[18%] h-96 w-96 rounded-full bg-white/10 blur-3xl" />
          <div className="relative mx-auto grid w-full max-w-[1240px] gap-12 px-5 pb-16 pt-[calc(var(--app-header-height)+4rem)] sm:px-8 md:pb-24 md:pt-[calc(var(--app-header-height)+6rem)] lg:grid-cols-[1.15fr_0.85fr] lg:items-end lg:px-10">
            <div>
              <p className="text-[20px] font-bold uppercase tracking-[0.16em] text-accent-light">How PrepVilla works</p>
              <h1 className="mt-5 max-w-3xl text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
                One clear journey. <p className="text-coral/75">Two ways to take part.</p>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-white/75 md:text-lg">
                Whether you are looking for support with learning or ready to share what you know, PrepVilla keeps discovery, communication, lessons, and payments connected.
              </p>
              <div className="mt-8 inline-flex rounded-2xl border border-white/15 bg-white/10 p-1.5 backdrop-blur" role="tablist" aria-label="Choose how PrepVilla works for you">
                {(["student", "tutor"] as const).map((item) => (
                  <button
                    key={item}
                    type="button"
                    role="tab"
                    aria-selected={audience === item}
                    onClick={() => setAudience(item)}
                    className={audience === item
                      ? "rounded-xl bg-white px-5 py-3 text-sm font-semibold text-primary-deep shadow-lg"
                      : "rounded-xl px-5 py-3 text-sm font-semibold text-white/75 transition hover:bg-white/10 hover:text-white"
                    }
                  >
                    {item === "student" ? "I am a student" : "I am a tutor"}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/15 bg-white/10 p-6 shadow-[0_28px_80px_rgba(0,0,0,0.2)] backdrop-blur-md sm:p-8">
              <div className="flex items-center justify-between border-b border-white/15 pb-5">
                <span className="text-sm font-semibold text-white/70">The journey at a glance</span>
                <span className="h-2.5 w-2.5 rounded-full bg-accent-light shadow-[0_0_0_6px_rgba(255,138,115,0.16)]" />
              </div>
              <div className="space-y-4 pt-5">
                {journey.highlights.map((highlight, index) => (
                  <div key={highlight} className="flex items-center gap-4">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--palette-coral),var(--palette-plum))] text-xs font-bold text-white shadow-lg">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="text-base font-semibold text-white/90">{highlight}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1240px] px-5 py-16 sm:px-8 md:py-24 lg:px-10">
          <div className="grid gap-10 lg:grid-cols-[230px_1fr]">
            <aside>
              <div className="sticky top-28 rounded-2xl border border-border bg-white/75 p-5 shadow-sm backdrop-blur">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">{journey.label}</p>
                <p className="mt-3 text-sm leading-6 text-muted">Follow each stage to see what happens and what you can manage from your account.</p>
                <Link href={journey.ctaHref} className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-accent-hover transition hover:gap-3">
                  {journey.ctaLabel} <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </aside>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-secondary-color-deep">{journey.label}</p>
              <h2 className="brand-heading mt-3 max-w-4xl text-3xl font-bold leading-tight tracking-tight text-primary-deep md:text-5xl">
                {journey.title}
              </h2>
              <p className="mt-5 max-w-3xl text-base leading-8 text-muted md:text-lg">{journey.description}</p>

              <div className="mt-12 grid gap-5">
                {journey.steps.map((step, index) => {
                  const Icon = step.icon;
                  return (
                    <article key={step.title} className="group rounded-[1.75rem] border border-border bg-white/80 p-6 shadow-[0_16px_45px_rgba(15,23,40,0.05)] transition hover:-translate-y-0.5 hover:border-info-border hover:shadow-[0_20px_50px_rgba(15,23,40,0.08)] md:p-8">
                      <div className="grid gap-6 md:grid-cols-[72px_1fr]">
                        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--palette-navy),var(--palette-plum))] text-white shadow-lg shadow-primary-deep/15">
                          <Icon className="h-7 w-7" />
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h3 className="text-xl font-semibold text-primary-deep md:text-2xl">{step.title}</h3>
                            <span className="text-sm font-bold text-accent">STEP {String(index + 1).padStart(2, "0")}</span>
                          </div>
                          <p className="mt-3 text-sm leading-7 text-muted md:text-base">{step.description}</p>
                          <ul className="mt-5 grid gap-3 lg:grid-cols-3">
                            {step.details.map((detail) => (
                              <li key={detail} className="flex gap-2.5 rounded-xl bg-surface-2/70 p-3 text-sm leading-6 text-foreground/75">
                                <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-accent" />
                                <span>{detail}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-black/8 bg-surface-2/65">
          <div className="mx-auto w-full max-w-[1240px] px-5 py-16 sm:px-8 md:py-20 lg:px-10">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Built into every journey</p>
              <h2 className="brand-heading mt-4 text-3xl font-bold tracking-tight text-primary-deep md:text-4xl">Clearer tools for students and tutors</h2>
            </div>
            <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {sharedBenefits.map((benefit) => {
                const Icon = benefit.icon;
                return (
                  <article key={benefit.title} className="rounded-2xl border border-white/80 bg-white/75 p-5 shadow-sm">
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent-soft text-accent-hover">
                      <Icon className="h-5 w-5" />
                    </span>
                    <h3 className="mt-5 text-lg font-semibold text-primary-deep">{benefit.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted">{benefit.description}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1240px] px-5 py-16 sm:px-8 md:py-24 lg:px-10">
          <div className="relative overflow-hidden rounded-[2rem] bg-[linear-gradient(135deg,var(--palette-coral)_0%,var(--palette-plum)_48%,var(--palette-navy)_100%)] p-8 text-white shadow-[0_28px_65px_rgba(15,23,40,0.2)] md:p-12">
            <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/15 blur-3xl" />
            <div className="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-white/80"><Star className="h-4 w-4" /> Start your PrepVilla journey</div>
                <h2 className="brand-heading mt-3 max-w-3xl text-3xl font-bold tracking-tight md:text-4xl">Ready to learn, teach, or explore what is possible?</h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-white/75 md:text-base">Choose the path that fits you today. You can also visit the FAQ page for detailed answers about accounts, lessons, payments, verification, and support.</p>
              </div>
              <div className="flex flex-wrap gap-3 lg:flex-col">
                <Link href={journey.ctaHref}>
                  <Button size="lg" variant="secondary" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    {journey.ctaLabel}
                  </Button>
                </Link>
                <Link href="/dashboard/faq" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/40 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">
                  <CircleDollarSign className="h-4 w-4" /> Read FAQs
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
