"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type TransitionEvent } from "react";
import type { TutorCard } from "@prepvilla/types";
import {
  ArrowRight,
  BadgeCheck,
  BookOpen,
  BookOpenCheck,
  BriefcaseBusiness,
  CalendarCheck2,
  ChevronLeft,
  ChevronRight,
  Code2,
  Cpu,
  FlaskConical,
  GraduationCap,
  Hammer,
  HeartHandshake,
  Landmark,
  Languages,
  LaptopMinimalCheck,
  MessageCircle,
  Palette,
  Search,
  ShieldCheck,
  Sigma,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { Button } from "../shared/Button";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import { FEATURED_SUBJECT_CATEGORY_KEYS, findSubjectCategoryByKey } from "../shared/nigeriaData";
import { TutorCardView } from "../tutors/TutorCardView";

type TutorsResponse = { results: TutorCard[] };
type FavoriteResponse = { ok: boolean; isFavorited: boolean };

type FeaturedSubjectCategoryKey = (typeof FEATURED_SUBJECT_CATEGORY_KEYS)[number];

const SUBJECT_CATEGORY_ICONS: Record<FeaturedSubjectCategoryKey, typeof Sigma> = {
  mathematics: Sigma,
  english: BookOpen,
  sciences: FlaskConical,
  programming: Code2,
  humanities: Landmark,
  "business & finance": BriefcaseBusiness,
  technology: Cpu,
  vocational: Hammer,
  "arts & creative": Palette,
  languages: Languages,
  "exam-prep": Sparkles,
};

const POPULAR_SUBJECTS = FEATURED_SUBJECT_CATEGORY_KEYS.flatMap((key) => {
  const category = findSubjectCategoryByKey(key);
  if (!category) return [];
  return [{ ...category, icon: SUBJECT_CATEGORY_ICONS[key] }];
});

const LEARNING_STEPS = [
  {
    number: "01",
    icon: Search,
    title: "Search with purpose",
    description: "Filter by subject, location, rate, language, and teaching mode to find promising matches quickly.",
  },
  {
    number: "02",
    icon: MessageCircle,
    title: "Compare the fit",
    description: "Review clear profiles, teaching styles, reviews, and verification details before you decide.",
  },
  {
    number: "03",
    icon: CalendarCheck2,
    title: "Request a lesson",
    description: "Share your goals, choose a preferred time, and start a structured conversation with your tutor.",
  },
  {
    number: "04",
    icon: BookOpenCheck,
    title: "Keep making progress",
    description: "Manage bookings, messages, availability, and reviews from one connected learning space.",
  },
];

const WHY_PREPVILLA = [
  {
    icon: BadgeCheck,
    title: "Verified tutor profiles",
    description: "See tutor verification status, subjects, rates, and teaching modes before you reach out.",
    iconClassName: "bg-accent-soft text-accent-hover",
  },
  {
    icon: HeartHandshake,
    title: "A better learning fit",
    description: "Compare real teaching details so you can choose someone who matches your goals and pace.",
    iconClassName: "bg-primary-soft text-primary-deep",
  },
  {
    icon: MessageCircle,
    title: "Direct communication",
    description: "Ask questions, discuss expectations, and keep important lesson conversations organized.",
    iconClassName: "bg-[rgba(245,184,65,0.18)] text-[#8b5e00]",
  },
  {
    icon: CalendarCheck2,
    title: "Flexible lesson planning",
    description: "Find online or face-to-face tutors and request lessons around real schedules.",
    iconClassName: "bg-[rgba(16,185,129,0.14)] text-emerald-700",
  },
  {
    icon: ShieldCheck,
    title: "Trust that grows",
    description: "Use verification, reviews, and clear profiles to make every next step feel more confident.",
    iconClassName: "bg-[rgba(99,102,241,0.14)] text-indigo-700",
  },
  {
    icon: LaptopMinimalCheck,
    title: "Learning that fits real life",
    description: "Choose a learning arrangement that works for your location, availability, and preferred format.",
    iconClassName: "bg-[rgba(139,97,120,0.16)] text-secondary-color-deep",
  },
];

const VISIBLE_SUBJECT_CATEGORY_COUNT = 5;
const SUBJECT_CATEGORY_CARD_WIDTH = "calc((100% - 2rem) / 5)";
const SUBJECT_CATEGORY_SLOT_OFFSET = `calc(${SUBJECT_CATEGORY_CARD_WIDTH} + 0.5rem)`;

type SubjectCarouselDirection = -1 | 0 | 1;

function wrapSubjectCategoryIndex(index: number) {
  return ((index % POPULAR_SUBJECTS.length) + POPULAR_SUBJECTS.length) % POPULAR_SUBJECTS.length;
}

function getSubjectCarouselItems(startIndex: number) {
  return Array.from({ length: VISIBLE_SUBJECT_CATEGORY_COUNT + 2 }, (_, offset) => {
    const itemIndex = wrapSubjectCategoryIndex(startIndex + offset - 1);
    return POPULAR_SUBJECTS[itemIndex];
  });
}

export function HomePage() {
  const [tutors, setTutors] = useState<TutorCard[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const [subjectCategoryStartIndex, setSubjectCategoryStartIndex] = useState(0);
  const [subjectCarouselDirection, setSubjectCarouselDirection] = useState<SubjectCarouselDirection>(0);
  const [isSubjectCarouselAnimating, setIsSubjectCarouselAnimating] = useState(false);
  const role = useAuthStore((s) => s.role);
  const isLoggedIn = useAuthStore((s) => Boolean(s.accessToken));
  const canFavorite = isLoggedIn && role === "student";

  const featuredTutors = useMemo(() => tutors.slice(0, 8), [tutors]);
  const verifiedTutorsCount = useMemo(
    () => tutors.filter((t) => t.verificationStatus === "approved").length,
    [tutors],
  );
  const subjectCarouselItems = useMemo(
    () => getSubjectCarouselItems(subjectCategoryStartIndex),
    [subjectCategoryStartIndex],
  );

  async function loadTutors() {
    setIsLoading(true);
    setError(null);
    const res = await api.get<TutorsResponse>("/api/tutors");
    if (!res.ok) {
      setTutors([]);
      setError(res.error ?? "Failed to load tutors");
      setIsLoading(false);
      return;
    }
    setTutors(res.data.results ?? []);
    setIsLoading(false);
  }

  useEffect(() => {
    void loadTutors();

    const handleRefresh = () => {
      void loadTutors();
    };
    window.addEventListener("refresh-home-tutors", handleRefresh);
    return () => {
      window.removeEventListener("refresh-home-tutors", handleRefresh);
    };
  }, []);

  function handleSubjectCarouselMove(direction: SubjectCarouselDirection) {
    if (direction === 0 || isSubjectCarouselAnimating) return;
    setIsSubjectCarouselAnimating(true);
    setSubjectCarouselDirection(direction);
  }

  function handleSubjectCarouselTransitionEnd(event: TransitionEvent<HTMLDivElement>) {
    if (event.target !== event.currentTarget) return;
    if (!isSubjectCarouselAnimating || subjectCarouselDirection === 0) return;
    setIsSubjectCarouselAnimating(false);
    setSubjectCategoryStartIndex((current) => wrapSubjectCategoryIndex(current + subjectCarouselDirection));
    setSubjectCarouselDirection(0);
  }

  const subjectCarouselTranslate =
    subjectCarouselDirection === -1
      ? "0"
      : subjectCarouselDirection === 1
        ? `calc(-2 * (${SUBJECT_CATEGORY_SLOT_OFFSET}))`
        : `calc(-1 * (${SUBJECT_CATEGORY_SLOT_OFFSET}))`;

  async function handleFavoriteChange(tutorId: string, nextFavorited: boolean) {
    if (!canFavorite) return;
    setFavoriteError(null);
    const res = nextFavorited
      ? await api.post<FavoriteResponse>(`/api/me/favorite-tutors/${tutorId}`)
      : await api.delete<FavoriteResponse>(`/api/me/favorite-tutors/${tutorId}`);

    if (!res.ok) {
      setFavoriteError(res.error ?? "Unable to update favorite list.");
      throw new Error(res.error ?? "Favorite update failed");
    }

    setTutors((prev) =>
      prev.map((item) => (item.id === tutorId ? { ...item, isFavorited: nextFavorited } : item)),
    );
  }

  return (
    <div className="brand-page min-h-screen overflow-hidden">
      <AppHeader overlay />

      <main className="hero-under-header mx-auto w-full max-w-[1480px] px-4 pb-14 md:px-4">
        <section className="brand-hero home-hero-coral hero-fill-screen home-hero-band relative overflow-hidden rounded-b-[40px] text-white">
          <div className="absolute -right-20 -top-24 h-80 w-80 rounded-full bg-accent/20 blur-3xl" />
          <div className="absolute -bottom-28 left-1/3 h-96 w-96 rounded-full bg-secondary-color/25 blur-3xl" />
          <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(rgba(255,255,255,0.26)_1px,transparent_1px)] [background-size:28px_28px]" />

          <div className="relative mx-auto w-full max-w-[1480px] px-6 pb-8 pt-[calc(var(--app-header-height)+2.75rem)] md:px-10 md:pb-10 md:pt-[calc(var(--app-header-height)+4rem)]">
            <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/85 backdrop-blur">
                  <Sparkles className="h-3.5 w-3.5 text-accent-light" />
                  A better way to learn
                </div>
                <h1 className="mt-6 text-4xl font-semibold leading-[1.08] tracking-tight md:text-6xl">
                  Find the right tutor.
                  <span className="mt-2 block text-accent-light">Make progress with confidence.</span>
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-8 text-white/80 md:text-lg">
                  Discover verified tutors across Nigeria, compare teaching styles, and choose a learning experience that fits your goals, schedule, and budget.
                </p>

                <div className="mt-8 flex flex-wrap gap-3">
                  <Link href="/search">
                    <Button size="lg" variant="secondary" leftIcon={<Search className="h-4 w-4" />}>
                      Find a tutor
                    </Button>
                  </Link>
                  <Link href="/signup/tutor">
                    <Button size="lg" variant="outline" className="border-white/60 text-white hover:bg-white/15 hover:text-white">
                      Become a tutor
                    </Button>
                  </Link>
                </div>

                <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm text-white/75">
                  <span className="inline-flex items-center gap-2">
                    <BadgeCheck className="h-4 w-4 text-accent-light" />
                    Profiles built for trust
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <MessageCircle className="h-4 w-4 text-accent-light" />
                    Direct tutor conversations
                  </span>
                </div>
              </div>

              <div className="relative mx-auto w-full max-w-xl">
                <div className="rounded-[2rem] border border-white/20 bg-white/10 p-5 shadow-[0_28px_70px_rgba(15,23,40,0.25)] backdrop-blur md:p-7">
                  <div className="flex items-start justify-between gap-4 border-b border-white/15 pb-5">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-light">The PrepVilla learning loop</p>
                      <h2 className="mt-2 text-2xl font-semibold">From first search to real progress.</h2>
                    </div>
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-accent text-white">
                      <GraduationCap className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3">
                    {[
                      { icon: Search, label: "Discover", description: "Find tutors by what and how you want to learn." },
                      { icon: BadgeCheck, label: "Choose confidently", description: "Use profile details and verification to compare the fit." },
                      { icon: CalendarCheck2, label: "Learn consistently", description: "Request lessons and keep your learning journey connected." },
                    ].map((item, index) => {
                      const Icon = item.icon;
                      return (
                        <div key={item.label} className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 p-3">
                          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-primary-deep">
                            <Icon className="h-4 w-4" />
                          </span>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 text-sm font-semibold">
                              <span className="text-accent-light">0{index + 1}</span>
                              {item.label}
                            </div>
                            <p className="mt-0.5 text-xs leading-5 text-white/65">{item.description}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-5 grid grid-cols-3 gap-2 border-t border-white/15 pt-5">
                    <div className="rounded-xl bg-white/10 p-3 text-center">
                      <div className="text-2xl font-semibold">{tutors.length}</div>
                      <div className="mt-1 text-[11px] text-white/65">Listed tutors</div>
                    </div>
                    <div className="rounded-xl bg-white/10 p-3 text-center">
                      <div className="text-2xl font-semibold">{verifiedTutorsCount}</div>
                      <div className="mt-1 text-[11px] text-white/65">Verified profiles</div>
                    </div>
                    <div className="rounded-xl bg-white/10 p-3 text-center">
                      <div className="text-2xl font-semibold">4.8</div>
                      <div className="mt-1 text-[11px] text-white/65">Average rating</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="relative flex justify-center px-4 pb-7 md:px-8">
            <div className="flex w-full max-w-[980px] items-center justify-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={() => handleSubjectCarouselMove(-1)}
                disabled={isSubjectCarouselAnimating}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/40 bg-white/80 text-primary-deep transition hover:border-accent/35 hover:text-accent disabled:cursor-not-allowed disabled:opacity-45"
                aria-label="Scroll subject categories left"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <div className="min-w-0 flex-1 rounded-[28px] border border-white/30 bg-white/10 p-2">
                <div className="overflow-hidden">
                  <div
                    className={`flex gap-2 ${isSubjectCarouselAnimating ? "transition-transform duration-300 ease-out" : ""}`}
                    style={{ transform: `translateX(${subjectCarouselTranslate})` }}
                    onTransitionEnd={handleSubjectCarouselTransitionEnd}
                  >
                    {subjectCarouselItems.map((item, index) => {
                      const Icon = item.icon;
                      return (
                        <Link
                          key={`${item.key}-${subjectCategoryStartIndex}-${index}`}
                          href={`/search?subjectCategory=${encodeURIComponent(item.key)}`}
                          className="group flex h-[58px] shrink-0 flex-col items-center justify-center rounded-2xl border border-white/60 bg-white px-2 py-1 text-center transition duration-200 hover:-translate-y-1 hover:border-secondary-color/40 hover:bg-secondary-color-soft focus-visible:border-secondary-color/40 focus-visible:bg-secondary-color-soft"
                          style={{ width: SUBJECT_CATEGORY_CARD_WIDTH }}
                        >
                          <Icon className="h-4 w-5 text-accent transition duration-200 group-hover:scale-120" />
                          <div className="mt-1 text-[12px] font-bold leading-3 text-primary-deep transition duration-200 group-hover:scale-120">{item.label}</div>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleSubjectCarouselMove(1)}
                disabled={isSubjectCarouselAnimating}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/40 bg-white/80 text-primary-deep transition hover:border-accent/35 hover:text-accent disabled:cursor-not-allowed disabled:opacity-45"
                aria-label="Scroll subject categories right"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>

        <section id="featured-tutors" className="mb-60 mt-14 text-black">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Explore the community</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-primary-deep md:text-3xl">Meet tutors ready to help you grow</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">Browse a selection of tutors, then open full search when you are ready to narrow down your options.</p>
            </div>
            <Link href="/search">
              <Button variant="secondary" rightIcon={<ArrowRight className="h-4 w-4" />}>
                Open full search
              </Button>
            </Link>
          </div>

          {favoriteError ? (
            <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{favoriteError}</div>
          ) : null}

          {error ? (
            <div className="rounded-2xl border border-border bg-surface p-5 text-sm text-black">
              <div className="font-semibold">Could not load tutors</div>
              <div className="mt-1 text-black/70">{error}</div>
            </div>
          ) : isLoading ? (
            <div className="featured-tutor-grid">
              {Array.from({ length: 8 }).map((_, idx) => (
                <div key={idx} className="h-[420px] animate-pulse rounded-3xl border border-border bg-surface" />
              ))}
            </div>
          ) : featuredTutors.length === 0 ? (
            <div className="rounded-2xl border border-border bg-surface p-5 text-sm text-black/70">No tutors are listed yet.</div>
          ) : (
            <div className="featured-tutor-grid">
              {featuredTutors.map((tutor) => (
                <TutorCardView
                  key={tutor.id}
                  tutor={tutor}
                  isFavorited={Boolean(tutor.isFavorited)}
                  onFavoriteChange={handleFavoriteChange}
                />
              ))}
            </div>
          )}
        </section>

        <section className="mt-16 rounded-[2rem] border border-[rgba(139,97,120,0.16)] bg-surface/80 p-6 shadow-[0_20px_45px_rgba(15,23,40,0.05)] md:p-10">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">Why PrepVilla</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-primary-deep md:text-4xl">A smarter way to choose how you learn</h2>
            <p className="mt-4 text-base leading-7 text-muted">We make the important details easier to see, so students can choose with confidence and tutors can build meaningful learning relationships.</p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {WHY_PREPVILLA.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="rounded-2xl border border-border bg-white/75 p-5 transition duration-200 hover:-translate-y-1 hover:border-info-border hover:shadow-lg">
                  <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${item.iconClassName}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-primary-deep">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section id="how-it-works" className="mt-16 px-1 md:px-6">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent">How it works</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-primary-deep md:text-4xl">Keep the whole learning journey connected</h2>
            <p className="mt-4 text-base leading-7 text-muted">The right tutor is only the beginning. PrepVilla gives you a clear path from discovery to the next lesson.</p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {LEARNING_STEPS.map((step) => {
              const Icon = step.icon;
              return (
                <article key={step.number} className="rounded-[1.75rem] border border-border bg-surface p-6 shadow-sm">
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

        <section className="mt-16 grid gap-5 md:grid-cols-2">
          <article className="rounded-[2rem] border border-white/70 bg-surface p-7 shadow-[0_18px_42px_rgba(15,23,40,0.06)] md:p-9">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent-hover">
              <UsersRound className="h-6 w-6" />
            </div>
            <h2 className="mt-6 text-2xl font-semibold text-primary-deep">For students</h2>
            <p className="mt-3 leading-7 text-muted">Discover tutors by subject, rate, location, language, and teaching mode. Compare profiles, ask questions, request a lesson, and keep your bookings and conversations together.</p>
            <Link href="/search" className="mt-7 inline-flex items-center gap-2 text-sm font-semibold text-accent-hover transition hover:gap-3">
              Explore tutors <ArrowRight className="h-4 w-4" />
            </Link>
          </article>

          <article className="rounded-[2rem] border border-white/10 bg-primary-deep p-7 text-white shadow-[0_18px_42px_rgba(15,23,40,0.15)] md:p-9">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-accent-light">
              <GraduationCap className="h-6 w-6" />
            </div>
            <h2 className="mt-6 text-2xl font-semibold">For tutors</h2>
            <p className="mt-3 leading-7 text-white/70">Create a credible profile, complete verification, set your rates and availability, respond to lesson requests, and build relationships with students who are ready to learn.</p>
            <Link href="/signup/tutor" className="mt-7 inline-flex items-center gap-2 text-sm font-semibold text-accent-light transition hover:gap-3">
              Join as a tutor <ArrowRight className="h-4 w-4" />
            </Link>
          </article>
        </section>

        <section className="relative mt-16 overflow-hidden rounded-[2rem] bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-navy)_58%,var(--palette-coral)_100%)] px-6 py-14 text-center text-white shadow-[0_24px_56px_rgba(15,23,40,0.2)] md:px-12 md:py-20">
          <div className="absolute -right-12 -top-20 h-64 w-64 rounded-full bg-accent/25 blur-3xl" />
          <div className="absolute -bottom-24 left-10 h-64 w-64 rounded-full bg-secondary-color/25 blur-3xl" />
          <div className="relative mx-auto max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Your next step starts here</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-5xl">Ready to find your learning match?</h2>
            <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-white/75 md:text-lg">Join a growing learning community built around clearer choices, trusted tutors, and progress that lasts.</p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link href="/search">
                <Button size="lg" variant="secondary" rightIcon={<ArrowRight className="h-4 w-4" />}>
                  Start searching
                </Button>
              </Link>
              <Link href="/signup/tutor">
                <Button size="lg" variant="outline" className="border-white/60 text-white hover:bg-white/15 hover:text-white">
                  Teach on PrepVilla
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
