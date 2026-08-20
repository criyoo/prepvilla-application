import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  BookOpenCheck,
  CalendarCheck2,
  GraduationCap,
  HeartHandshake,
  LaptopMinimalCheck,
  MessageCircle,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { Button } from "../shared/Button";

const learningSteps = [
  {
    number: "01",
    icon: ShieldCheck,
    title: "Find trusted tutors",
    description: "Explore tutor profiles with clear subjects, rates, teaching modes, and verification status.",
  },
  {
    number: "02",
    icon: MessageCircle,
    title: "Start a conversation",
    description: "Ask questions, compare teaching styles, and make sure the learning fit feels right.",
  },
  {
    number: "03",
    icon: CalendarCheck2,
    title: "Book a lesson",
    description: "Choose a preferred time, share your goals, and send a structured lesson request.",
  },
  {
    number: "04",
    icon: BookOpenCheck,
    title: "Keep making progress",
    description: "Manage bookings, messages, availability, and reviews in one connected place.",
  },
];

const trustPrinciples = [
  {
    icon: BadgeCheck,
    title: "Verification with purpose",
    description: "Tutor verification gives students more context and helps tutors build credible public profiles.",
  },
  {
    icon: HeartHandshake,
    title: "People before process",
    description: "The platform keeps communication personal while giving both sides the structure to move forward confidently.",
  },
  {
    icon: LaptopMinimalCheck,
    title: "Learning that fits real life",
    description: "Students can find tutors for online or face-to-face lessons, with availability and expectations made clear.",
  },
];

export function AboutPage() {
  return (
    <div className="brand-page min-h-screen">
      <AppHeader overlay />

      <main className="hero-under-header">
        <section className="relative overflow-hidden border-b border-[rgba(139,97,120,0.16)] bg-[linear-gradient(135deg,#fff7f1_0%,#fffdf8_52%,#efe2e8_100%)]">
          <div className="absolute -right-24 -top-28 h-80 w-80 rounded-full bg-accent/15 blur-3xl" />
          <div className="absolute -bottom-36 left-1/3 h-96 w-96 rounded-full bg-primary/12 blur-3xl" />
          <div className="relative mx-auto grid w-full max-w-[1480px] gap-10 px-4 pb-16 pt-[calc(var(--app-header-height)+4rem)] md:px-10 md:pb-24 md:pt-[calc(var(--app-header-height)+6rem)] lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-accent/25 bg-surface/75 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-accent-hover shadow-sm">
                <Sparkles className="h-3.5 w-3.5" />
                About PrepVilla
              </div>
              <h1 className="mt-6 text-4xl font-semibold leading-tight tracking-tight text-primary-deep md:text-6xl">
                Learning works better when trust comes first.
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-muted md:text-lg">
                PrepVilla is a verified-teacher marketplace helping students across Nigeria find the right tutor, book lessons with confidence, and keep their learning journey moving.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/search">
                  <Button size="lg" variant="primary" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    Find a tutor
                  </Button>
                </Link>
                <Link href="/signup/tutor">
                  <Button size="lg" variant="secondary">
                    Become a tutor
                  </Button>
                </Link>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-md rounded-[2rem] border border-white/70 bg-primary-deep p-6 text-white shadow-[0_28px_70px_rgba(15,23,40,0.2)] md:p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-white">
                <GraduationCap className="h-6 w-6" />
              </div>
              <h2 className="mt-6 text-2xl font-semibold leading-tight md:text-3xl">
                A clearer path from curiosity to progress.
              </h2>
              <p className="mt-4 text-sm leading-7 text-white/75 md:text-base">
                Students get a simpler way to discover and choose tutors. Tutors get the tools to present their experience, manage availability, and teach with confidence.
              </p>
              <div className="mt-7 grid gap-3 text-sm font-medium text-white/90">
                <div className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/8 px-4 py-3">
                  <BadgeCheck className="h-5 w-5 shrink-0 text-accent-light" />
                  Verified tutor profiles
                </div>
                <div className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/8 px-4 py-3">
                  <MessageCircle className="h-5 w-5 shrink-0 text-accent-light" />
                  Direct, organized communication
                </div>
                <div className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/8 px-4 py-3">
                  <CalendarCheck2 className="h-5 w-5 shrink-0 text-accent-light" />
                  Bookings built around real schedules
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1200px] px-4 py-16 md:px-8 md:py-24">
          <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Why PrepVilla exists</p>
              <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-primary-deep md:text-4xl">
                The right tutor can change what feels possible.
              </h2>
            </div>
            <div className="space-y-5 text-base leading-8 text-muted md:text-lg">
              <p>
                Finding a tutor should not mean sorting through uncertainty. Students need a clear view of who they are learning with, what the tutor teaches, and whether the arrangement fits their goals and schedule.
              </p>
              <p>
                Tutors need more than a listing. They need a professional way to share their experience, complete verification, set availability, respond to requests, and build lasting trust with students.
              </p>
              <p>
                PrepVilla brings those needs together in one marketplace designed around confidence, communication, and meaningful progress.
              </p>
            </div>
          </div>
        </section>

        <section className="border-y border-[rgba(139,97,120,0.15)] bg-surface-2/65">
          <div className="mx-auto w-full max-w-[1200px] px-4 py-16 md:px-8 md:py-24">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Built for both sides of learning</p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight text-primary-deep md:text-4xl">
                Better tools for students. A stronger home for tutors.
              </h2>
            </div>
            <div className="mt-12 grid gap-5 md:grid-cols-2">
              <article className="rounded-[2rem] border border-white/80 bg-surface p-7 shadow-[0_18px_42px_rgba(15,23,40,0.06)] md:p-9">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent-hover">
                  <UsersRound className="h-6 w-6" />
                </div>
                <h3 className="mt-6 text-2xl font-semibold text-primary-deep">For students</h3>
                <p className="mt-3 leading-7 text-muted">
                  Discover tutors by subject, rate, location, language, and teaching mode. Compare profiles, ask questions, request a lesson, and keep your bookings and conversations together.
                </p>
                <Link href="/search" className="mt-7 inline-flex items-center gap-2 text-sm font-semibold text-accent-hover transition hover:gap-3">
                  Explore tutors <ArrowRight className="h-4 w-4" />
                </Link>
              </article>

              <article className="rounded-[2rem] border border-white/80 bg-primary-deep p-7 text-white shadow-[0_18px_42px_rgba(15,23,40,0.14)] md:p-9">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/12 text-accent-light">
                  <GraduationCap className="h-6 w-6" />
                </div>
                <h3 className="mt-6 text-2xl font-semibold">For tutors</h3>
                <p className="mt-3 leading-7 text-white/72">
                  Create a credible profile, complete verification, set your rates and availability, respond to lesson requests, and build relationships with students who are ready to learn.
                </p>
                <Link href="/signup/tutor" className="mt-7 inline-flex items-center gap-2 text-sm font-semibold text-accent-light transition hover:gap-3">
                  Join as a tutor <ArrowRight className="h-4 w-4" />
                </Link>
              </article>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1200px] px-4 py-16 md:px-8 md:py-24">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">How it works</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-primary-deep md:text-4xl">
              From first search to first lesson, everything stays connected.
            </h2>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {learningSteps.map((step) => {
              const Icon = step.icon;
              return (
                <article key={step.number} className="relative rounded-[1.75rem] border border-border bg-surface p-6 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-soft text-primary-deep">
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="text-sm font-semibold text-accent">{step.number}</span>
                  </div>
                  <h3 className="mt-6 text-xl font-semibold text-primary-deep">{step.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-muted">{step.description}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="bg-primary-deep text-white">
          <div className="mx-auto w-full max-w-[1200px] px-4 py-16 md:px-8 md:py-24">
            <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent-light">What we believe</p>
                <h2 className="mt-4 text-3xl font-semibold leading-tight md:text-4xl">
                  Trust makes better learning possible.
                </h2>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                {trustPrinciples.map((principle) => {
                  const Icon = principle.icon;
                  return (
                    <article key={principle.title} className="rounded-[1.75rem] border border-white/12 bg-white/8 p-5">
                      <Icon className="h-6 w-6 text-accent-light" />
                      <h3 className="mt-5 text-lg font-semibold">{principle.title}</h3>
                      <p className="mt-3 text-sm leading-7 text-white/70">{principle.description}</p>
                    </article>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1200px] px-4 py-16 md:px-8 md:py-24">
          <div className="rounded-[2rem] border border-accent/20 bg-[linear-gradient(135deg,rgba(240,100,73,0.12),rgba(239,226,232,0.7))] p-8 md:p-12">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent-hover">Our vision</p>
              <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-primary-deep md:text-4xl">
                A future where finding support for learning feels simple, safe, and human.
              </h2>
              <p className="mt-5 text-base leading-8 text-muted md:text-lg">
                We are building toward a learning marketplace where students can make informed choices, tutors can do their best work, and every lesson begins with a little more confidence.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/search">
                  <Button size="lg" variant="primary" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    Start learning
                  </Button>
                </Link>
                <Link href="/signup/tutor">
                  <Button size="lg" variant="outline">
                    Teach on PrepVilla
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
