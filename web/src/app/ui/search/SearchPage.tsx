"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useSearchParams } from "next/navigation";
import type { TutorCard } from "@prepvilla/types";
import { ArrowLeft, ArrowRight, Quote, SlidersHorizontal, Star } from "lucide-react";
import { AppHeader } from "../shared/AppHeader";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { Select } from "../shared/Select";
import { api } from "../shared/api";
import { useAuthStore } from "../shared/authStore";
import {
  FEATURED_SUBJECT_CATEGORY_KEYS,
  NIGERIA_STATE_CITIES,
  NIGERIA_STATES,
  findSubjectCategoryByKey,
  findSubjectCategoryByLabel,
  findSubjectCategoryBySubject,
  getSubjectsForCategory,
  subjectTermsMatch,
} from "../shared/nigeriaData";
import { TutorCardView } from "../tutors/TutorCardView";
import {
  SUBJECT_CATEGORY_OPTIONS,
  buildTutorApiSearchParams,
  buildTutorSearchParams,
  EMPTY_TUTOR_SEARCH_FILTERS,
  GENDER_OPTIONS,
  LANGUAGE_OPTIONS,
  parseTutorSearchParams,
  QUALIFICATION_OPTIONS,
  SUBJECT_OPTIONS,
  type TutorSearchFilters,
} from "./searchFilters";
import { LEARNING_CARD_IMAGES } from "./learningCardImages";

type TutorsResponse = { results: TutorCard[] };
type FavoriteResponse = { ok: boolean; isFavorited: boolean };

const SUBJECT_CHIPS = FEATURED_SUBJECT_CATEGORY_KEYS.flatMap((key) => {
  const category = findSubjectCategoryByKey(key);
  return category ? [category] : [];
});

const LEARNING_STEPS = [
  {
    key: "choose",
    step: "01",
    title: "Choose",
    description:
      "Browse tutors by budget, location, and teaching style, then shortlist the ones that match how you want to learn.",
  },
  {
    key: "exchange",
    step: "02",
    title: "Exchange",
    description:
      "Start the conversation, explain what you want to improve, and agree on a lesson plan that fits your schedule.",
  },
  {
    key: "progress",
    step: "03",
    title: "Make Progress",
    description:
      "Take lessons consistently, practise with confidence, and track clear improvement with the right tutor beside you.",
  },
] as const;

type LearningStepKey = (typeof LEARNING_STEPS)[number]["key"];

function getCascadeImageStyle(index: number, count: number): CSSProperties {
  if (count <= 1) {
    return {
      height: "372px",
      left: "50%",
      top: "8px",
      transform: "translateX(-50%) rotate(0deg)",
      width: "324px",
      zIndex: 40,
    };
  }

  const center = (count - 1) / 2;
  const distance = index - center;
  const absDistance = Math.abs(distance);
  const spread = count <= 3 ? 96 : count === 4 ? 76 : 60;
  const width = Math.max(140, 224 - absDistance * 24);
  const height = Math.max(176, 272 - absDistance * 30);
  const top = 8 + absDistance * 22;

  return {
    height: `${height}px`,
    left: `calc(50% + ${distance * spread}px)`,
    top: `${top}px`,
    transform: `translateX(-50%) rotate(${distance * 7}deg)`,
    width: `${width}px`,
    zIndex: Math.round(40 - absDistance * 5),
  };
}

const STUDENT_REVIEWS = [
  {
    name: "A. Adeyemi",
    label: "WAEC student, Lagos",
    rating: 5,
    text: "I moved from C6 to B2 in just 2 months. My tutor explained maths step by step and gave me confidence before exams.",
  },
  {
    name: "F. Usman",
    label: "JAMB student, Abuja",
    rating: 5,
    text: "The lessons were clear and practical. I liked that we focused on exactly where I was struggling.",
  },
  {
    name: "C. Okafor",
    label: "Parent, Port Harcourt",
    rating: 5,
    text: "My son's physics results improved quickly. The tutor was punctual, patient, and very professional.",
  },
];

const STATE_OPTIONS = [
  { value: "", label: "Any state" },
  ...NIGERIA_STATES.map((state) => ({ value: state, label: state })),
];

const OTHER_OPTION_VALUE = "__other__";
const SEARCH_RESULTS_PER_PAGE = 15;

function matchKnownSubject(value: string, choices?: string[]) {
  const normalizedValue = value.trim();

  if (!normalizedValue) {
    return "";
  }

  const nextChoices =
    choices ??
    SUBJECT_OPTIONS.filter((option) => option.value).map((option) => option.value);

  return nextChoices.find((option) => option.toLowerCase() === normalizedValue.toLowerCase()) ?? "";
}

function matchKnownSubjectCategory(value: string) {
  return findSubjectCategoryByKey(value)?.key ?? findSubjectCategoryByLabel(value)?.key ?? "";
}

function normalizeStateValue(state: string) {
  const normalizedState = state.trim();

  if (!normalizedState) {
    return "";
  }

  return (
    NIGERIA_STATES.find(
      (candidate) => candidate.toLowerCase() === normalizedState.toLowerCase(),
    ) ?? normalizedState
  );
}

function matchKnownLocationForState(state: string, location: string) {
  const normalizedState = normalizeStateValue(state);
  const normalizedLocation = location.trim();

  if (!normalizedState || !normalizedLocation) {
    return "";
  }

  return (
    (NIGERIA_STATE_CITIES[normalizedState] ?? []).find(
      (city) => city.toLowerCase() === normalizedLocation.toLowerCase(),
    ) ?? ""
  );
}

function normalizeFilters(filters: TutorSearchFilters): TutorSearchFilters {
  const normalizedCategory = matchKnownSubjectCategory(filters.subjectCategory);
  const normalizedSubject = matchKnownSubject(filters.subject) || filters.subject.trim();
  const derivedCategory = normalizedSubject
    ? findSubjectCategoryBySubject(normalizedSubject)?.key ?? normalizedCategory
    : normalizedCategory;
  const normalizedState = normalizeStateValue(filters.state);
  const normalizedLocation = filters.location.trim();

  return {
    ...filters,
    subjectCategory: derivedCategory,
    subject:
      derivedCategory && subjectTermsMatch(normalizedSubject, findSubjectCategoryByKey(derivedCategory)?.label ?? "")
        ? ""
        : normalizedSubject,
    state: normalizedState,
    location: normalizedState
      ? matchKnownLocationForState(normalizedState, normalizedLocation) || normalizedLocation
      : "",
  };
}

function deriveSubjectSelection(subjectCategory: string, subject: string) {
  const categorySubjects = getSubjectsForCategory(subjectCategory);
  return matchKnownSubject(subject, categorySubjects.length ? categorySubjects : undefined) || (subject.trim() ? OTHER_OPTION_VALUE : "");
}

function deriveLocationSelection(state: string, location: string) {
  if (!state.trim()) {
    return "";
  }

  return matchKnownLocationForState(state, location) || (location.trim() ? OTHER_OPTION_VALUE : "");
}

function tutorMatchesSubjectCategory(tutor: TutorCard, subjectCategory: string) {
  if (!subjectCategory) {
    return true;
  }

  const subjectsInCategory = getSubjectsForCategory(subjectCategory);
  if (subjectsInCategory.length === 0) {
    return true;
  }

  return tutor.subjects.some((subject) =>
    subjectsInCategory.some((candidate) => subjectTermsMatch(subject, candidate)),
  );
}

function tutorMatchesSubject(tutor: TutorCard, subject: string) {
  if (!subject.trim()) {
    return true;
  }

  return tutor.subjects.some((candidate) => subjectTermsMatch(candidate, subject));
}

export function SearchPage() {
  const searchParams = useSearchParams();
  const urlQueryKey = searchParams.toString();
  const initialFilters = normalizeFilters(parseTutorSearchParams(searchParams));
  const [filters, setFilters] = useState<TutorSearchFilters>(() =>
    initialFilters,
  );
  const [subjectSelection, setSubjectSelection] = useState(() =>
    deriveSubjectSelection(initialFilters.subjectCategory, initialFilters.subject),
  );
  const [locationSelection, setLocationSelection] = useState(() =>
    deriveLocationSelection(initialFilters.state, initialFilters.location),
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const [tutors, setTutors] = useState<TutorCard[]>([]);
  const [currentTutorPage, setCurrentTutorPage] = useState(0);
  const role = useAuthStore((s) => s.role);
  const isLoggedIn = useAuthStore((s) => Boolean(s.accessToken));
  const canFavorite = isLoggedIn && role === "student";
  const selectedCategory = useMemo(
    () => findSubjectCategoryByKey(filters.subjectCategory),
    [filters.subjectCategory],
  );
  const reviewSubject = filters.subject.trim() || selectedCategory?.label || "";
  const learningSubject = filters.subject.trim() || selectedCategory?.label || "";
  const cityChoices = NIGERIA_STATE_CITIES[filters.state] ?? [];
  const categorySubjects = useMemo(
    () => (selectedCategory ? selectedCategory.subjects : SUBJECT_OPTIONS.filter((option) => option.value).map((option) => option.value)),
    [selectedCategory],
  );
  const subjectOptions = useMemo(
    () => [
      {
        value: "",
        label: selectedCategory ? `All ${selectedCategory.label} subjects` : "All subjects",
      },
      ...categorySubjects.map((subject) => ({ value: subject, label: subject })),
      { value: OTHER_OPTION_VALUE, label: "Other subject" },
    ],
    [categorySubjects, selectedCategory],
  );
  const cityOptions = [
    {
      value: "",
      label: filters.state
        ? cityChoices.length
          ? "Any city"
          : "No cities available"
        : "Select a state first",
    },
    ...cityChoices.map((city) => ({
      value: city,
      label: city,
    })),
    ...(filters.state ? [{ value: OTHER_OPTION_VALUE, label: "Others" }] : []),
  ];

  useEffect(() => {
    const normalizedNext = normalizeFilters(parseTutorSearchParams(searchParams));
    setFilters((prev) => {
      if (
        prev.subjectCategory === normalizedNext.subjectCategory &&
        prev.subject === normalizedNext.subject &&
        prev.state === normalizedNext.state &&
        prev.location === normalizedNext.location &&
        prev.minRate === normalizedNext.minRate &&
        prev.maxRate === normalizedNext.maxRate &&
        prev.qualification === normalizedNext.qualification &&
        prev.gender === normalizedNext.gender &&
        prev.language === normalizedNext.language
      ) {
        return prev;
      }
      return normalizedNext;
    });
    setSubjectSelection(deriveSubjectSelection(normalizedNext.subjectCategory, normalizedNext.subject));
    setLocationSelection(deriveLocationSelection(normalizedNext.state, normalizedNext.location));
  }, [searchParams, urlQueryKey]);

  const pageQueryString = useMemo(() => buildTutorSearchParams(filters).toString(), [filters]);
  const apiQueryString = useMemo(() => buildTutorApiSearchParams(filters).toString(), [filters]);
  const filteredTutors = useMemo(
    () =>
      tutors.filter(
        (tutor) =>
          tutorMatchesSubjectCategory(tutor, filters.subjectCategory) &&
          tutorMatchesSubject(tutor, filters.subject),
      ),
    [filters.subject, filters.subjectCategory, tutors],
  );
  const totalTutorPages = useMemo(
    () => Math.max(1, Math.ceil(filteredTutors.length / SEARCH_RESULTS_PER_PAGE)),
    [filteredTutors.length],
  );
  const pagedTutors = useMemo(() => {
    const start = currentTutorPage * SEARCH_RESULTS_PER_PAGE;
    return filteredTutors.slice(start, start + SEARCH_RESULTS_PER_PAGE);
  }, [currentTutorPage, filteredTutors]);
  const isFirstTutorPage = currentTutorPage === 0;
  const isLastTutorPage = currentTutorPage >= totalTutorPages - 1;
  const learningTitle = learningSubject
    ? `Learning ${learningSubject} made simple`
    : "Learning with the right tutor made simple";
  const learningStepImages: Record<LearningStepKey, string[]> = LEARNING_CARD_IMAGES;

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setIsLoading(true);
      setError(null);
      const path = apiQueryString ? `/api/tutors?${apiQueryString}` : "/api/tutors";
      const res = await api.get<TutorsResponse>(path);
      if (cancelled) return;
      if (!res.ok) {
        setError(res.error ?? "Failed to load tutors");
        setTutors([]);
        setIsLoading(false);
        return;
      }
      setTutors(res.data.results ?? []);
      setIsLoading(false);
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [apiQueryString]);

  useEffect(() => {
    setCurrentTutorPage(0);
  }, [pageQueryString]);

  useEffect(() => {
    setCurrentTutorPage((prev) => Math.min(prev, Math.max(0, totalTutorPages - 1)));
  }, [totalTutorPages]);

  function updateFilter<K extends keyof TutorSearchFilters>(key: K, value: TutorSearchFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubjectCategoryChange(nextCategory: string) {
    const subjectsInCategory = getSubjectsForCategory(nextCategory);
    const nextSubject =
      filters.subject && subjectsInCategory.some((subject) => subjectTermsMatch(subject, filters.subject))
        ? filters.subject
        : "";

    setFilters((prev) => ({
      ...prev,
      subjectCategory: nextCategory,
      subject: nextSubject,
    }));
    setSubjectSelection(deriveSubjectSelection(nextCategory, nextSubject));
  }

  function handleSubjectChange(nextSubject: string) {
    if (nextSubject === OTHER_OPTION_VALUE) {
      setSubjectSelection(OTHER_OPTION_VALUE);
      setFilters((prev) => ({
        ...prev,
        subject: subjectSelection === OTHER_OPTION_VALUE ? prev.subject : "",
      }));
      return;
    }

    setSubjectSelection(nextSubject);
    updateFilter("subject", nextSubject);
  }

  function handleStateChange(nextState: string) {
    const nextLocation =
      nextState && locationSelection !== OTHER_OPTION_VALUE
        ? matchKnownLocationForState(nextState, filters.location)
        : "";

    setFilters((prev) => ({
      ...prev,
      state: nextState,
      location: nextLocation,
    }));
    setLocationSelection(nextLocation || "");
  }

  function handleLocationChange(nextLocation: string) {
    if (nextLocation === OTHER_OPTION_VALUE) {
      setLocationSelection(OTHER_OPTION_VALUE);
      setFilters((prev) => ({
        ...prev,
        location: locationSelection === OTHER_OPTION_VALUE ? prev.location : "",
      }));
      return;
    }

    setLocationSelection(nextLocation);
    updateFilter("location", nextLocation);
  }

  function resetFilters() {
    setFilters(EMPTY_TUTOR_SEARCH_FILTERS);
    setSubjectSelection("");
    setLocationSelection("");
  }

  function goToNextTutorPage() {
    if (isLastTutorPage) return;
    setCurrentTutorPage((prev) => Math.min(prev + 1, totalTutorPages - 1));
  }

  function goToPreviousTutorPage() {
    if (isFirstTutorPage) return;
    setCurrentTutorPage((prev) => Math.max(prev - 1, 0));
  }

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
    <div className="brand-page min-h-screen">
      <AppHeader overlay />
      <main className="hero-under-header mx-auto w-full max-w-[1350px] px-4 pb-12 md:px-8">
        <section className="brand-hero hero-fill-screen home-hero-band relative overflow-hidden rounded-b-[32px] text-white">
          <div className="absolute -right-12 -top-16 h-56 w-56 rounded-full bg-surface/22 blur-2xl" />
          <div className="absolute -bottom-20 left-1/4 h-52 w-52 rounded-full bg-accent/20 blur-3xl" />
          <div className="mx-auto w-full max-w-[1600px] px-4 md:px-8">
            <div className="relative px-6 pb-6 pt-[calc(var(--app-header-height)+1.5rem)] md:px-8 md:pb-8 md:pt-[calc(var(--app-header-height)+2rem)]">
              <p className="mt-12 text-sm font-semibold uppercase tracking-[0.2em] text-white/80 text-center">Tutor Discovery</p>
              <h1 className="mt-6 text-2xl font-bold leading-tight md:text-5xl text-center">
                Find a Tutor That Fits Your Learning Style
              </h1>
              <p className="mt-3 text-sm text-white/85 md:text-base text-center">
                Browse verified tutors by subject, city, language and budget. Save your favorites and compare before you book.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 justify-center">
                {SUBJECT_CHIPS.map((category) => (
                  (() => {
                    const isActive = filters.subjectCategory === category.key;
                    return (
                      <button
                        key={category.key}
                        type="button"
                        onClick={() => {
                          setSubjectSelection("");
                          setFilters((prev) => ({
                            ...prev,
                            subjectCategory: category.key,
                            subject: "",
                          }));
                        }}
                        className={`rounded-full border px-3 py-2 text-[10px] font-semibold backdrop-blur-sm transition ${isActive
                          ? "border-primary bg-primary text-white"
                          : "border-primary-soft/80 bg-primary-soft/85 text-primary-deep hover:border-primary hover:bg-primary hover:text-white"
                          }`}
                      >
                        {category.label}
                      </button>
                    );
                  })()
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="mt-6">
          <section className="form-panel min-w-0 rounded-3xl p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-[color:var(--palette-coral-deep)]" />
                <h2 className="text-[16px] font-semibold text-black">Filters</h2>
              </div>
              <Button variant="ghost" size="sm" onClick={resetFilters}>
                Reset
              </Button>
            </div>

            <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <Select
                label="Subject Category"
                value={filters.subjectCategory}
                onChange={(e) => handleSubjectCategoryChange(e.target.value)}
                options={SUBJECT_CATEGORY_OPTIONS}
              />
              <Select
                label="Subject"
                value={subjectSelection}
                onChange={(e) => handleSubjectChange(e.target.value)}
                options={subjectOptions}
              />
              {subjectSelection === OTHER_OPTION_VALUE ? (
                <Input
                  label="Other Subject"
                  value={filters.subject}
                  onChange={(e) => updateFilter("subject", e.target.value)}
                  placeholder="Enter a subject"
                />
              ) : null}
              <Select
                label="State"
                value={filters.state}
                onChange={(e) => handleStateChange(e.target.value)}
                options={STATE_OPTIONS}
              />
              <Select
                label="Location (City)"
                value={locationSelection}
                onChange={(e) => handleLocationChange(e.target.value)}
                options={cityOptions}
                disabled={!filters.state}
              />
              {locationSelection === OTHER_OPTION_VALUE ? (
                <Input
                  label="Other Location"
                  value={filters.location}
                  onChange={(e) => updateFilter("location", e.target.value)}
                  placeholder="Enter a city or town"
                />
              ) : null}
            </div>

            <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <Select
                label="Qualification"
                value={filters.qualification}
                onChange={(e) => updateFilter("qualification", e.target.value)}
                options={QUALIFICATION_OPTIONS}
              />
              <Select
                label="Gender"
                value={filters.gender}
                onChange={(e) => updateFilter("gender", e.target.value)}
                options={GENDER_OPTIONS}
              />
              <Select
                label="Language"
                value={filters.language}
                onChange={(e) => updateFilter("language", e.target.value)}
                options={LANGUAGE_OPTIONS}
              />
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-2">
                <Input
                  label="Min ₦/hr"
                  value={filters.minRate}
                  onChange={(e) => updateFilter("minRate", e.target.value)}
                  inputMode="numeric"
                  placeholder="2000"
                />
                <Input
                  label="Max ₦/hr"
                  value={filters.maxRate}
                  onChange={(e) => updateFilter("maxRate", e.target.value)}
                  inputMode="numeric"
                  placeholder="8200"
                />
              </div>
            </div>
          </section>

          <section className="mt-6 min-w-0">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Search Results</h2>
                <p className="text-sm text-muted">
                  {isLoading
                    ? "Finding tutors..."
                    : `${filteredTutors.length} tutor${filteredTutors.length === 1 ? "" : "s"} available`}
                </p>
              </div>
              {!canFavorite ? (
                <Link href="/login" className="text-xs text-muted underline decoration-dotted underline-offset-4">
                  Login as student to save favorites
                </Link>
              ) : null}
            </div>

            {favoriteError ? (
              <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {favoriteError}
              </div>
            ) : null}

            {error ? (
              <div className="rounded-2xl border border-border bg-surface p-5 text-sm">
                <div className="font-semibold">Could not load tutors</div>
                <div className="mt-1 text-muted">{error}</div>
              </div>
            ) : null}

            {isLoading ? (
              <div className="search-tutor-grid search-tutor-grid--large">
                {Array.from({ length: SEARCH_RESULTS_PER_PAGE }).map((_, i) => (
                  <div key={i} className="h-[500px] animate-pulse rounded-3xl border border-border bg-surface" />
                ))}
              </div>
            ) : filteredTutors.length === 0 ? (
              <div className="rounded-2xl border border-border bg-surface p-6 text-center">
                <h3 className="text-base font-semibold">No tutors match your filters</h3>
                <p className="mt-1 text-sm text-muted">Try widening your budget range or clearing a few filters.</p>
              </div>
            ) : (
              <>
                <div className="search-tutor-grid search-tutor-grid--large">
                  {pagedTutors.map((tutor) => (
                    <TutorCardView
                      key={tutor.id}
                      tutor={tutor}
                      size="wide"
                      isFavorited={Boolean(tutor.isFavorited)}
                      onFavoriteChange={handleFavoriteChange}
                    />
                  ))}
                </div>
                {totalTutorPages > 1 ? (
                  <div className="mt-6 flex justify-center">
                    <div className="flex flex-wrap items-center justify-center gap-3">
                      {isFirstTutorPage ? (
                        <button
                          type="button"
                          onClick={goToNextTutorPage}
                          className="flex h-11 w-11 items-center justify-center rounded-full bg-primary text-white transition hover:bg-primary-hover"
                          aria-label="Next tutor page"
                        >
                          <ArrowRight className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={goToPreviousTutorPage}
                          className="flex h-11 w-11 items-center justify-center rounded-full bg-primary text-white transition hover:bg-primary-hover"
                          aria-label="Previous tutor page"
                        >
                          <ArrowLeft className="h-4 w-4" />
                        </button>
                      )}
                      <Button
                        variant="secondary"
                        size="lg"
                        onClick={isLastTutorPage ? goToPreviousTutorPage : goToNextTutorPage}
                        className="min-w-[220px]"
                      >
                        See more tutors
                      </Button>
                      {!isFirstTutorPage && !isLastTutorPage ? (
                        <button
                          type="button"
                          onClick={goToNextTutorPage}
                          className="flex h-11 w-11 items-center justify-center rounded-full bg-primary text-white transition hover:bg-primary-hover"
                          aria-label="Next tutor page"
                        >
                          <ArrowRight className="h-4 w-4" />
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </section>
        </div>

        <section className="mt-12 rounded-[32px] border border-primary-soft bg-surface/95 p-6 shadow-sm md:p-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-deep">How It Works</p>
            <h3 className="mt-2 text-2xl font-semibold text-foreground md:text-3xl">{learningTitle}</h3>
            <p className="mt-3 text-sm leading-6 text-muted md:text-base">
              Choose a tutor, talk through your goals, and build momentum with lessons that are tailored to your level.
            </p>
          </div>

          <div className="mt-6 grid grid-cols-1 justify-center gap-4 lg:[grid-template-columns:repeat(3,minmax(0,340px))]">
            {LEARNING_STEPS.map((item) => {
              const images = learningStepImages[item.key];
              return (
                <article
                  key={item.step}
                  className="brand-learning-card w-full rounded-[28px] p-5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-4xl font-black tracking-tight text-primary-deep/20">{item.step}</span>
                  </div>
                  <h4 className="mt-8 text-[1.85rem] font-semibold leading-none text-foreground md:text-[2.1rem]">{item.title}</h4>
                  <p className="mt-3 text-sm leading-6 text-muted md:text-base">{item.description}</p>
                  <div className="relative mt-7 h-72 overflow-hidden">
                    {images.length > 0 ? (
                      images.map((src, index) => {
                        const imageStyle = getCascadeImageStyle(index, images.length);
                        const width =
                          typeof imageStyle.width === "number"
                            ? imageStyle.width
                            : Number.parseInt(`${imageStyle.width ?? 224}`, 10);
                        const height =
                          typeof imageStyle.height === "number"
                            ? imageStyle.height
                            : Number.parseInt(`${imageStyle.height ?? 272}`, 10);

                        return (
                          <Image
                            key={`${item.key}-${index}`}
                            src={src}
                            alt={`${item.title} step preview ${index + 1}`}
                            width={width}
                            height={height}
                            sizes="(min-width: 1024px) 224px, 45vw"
                            className="absolute rounded-[30px] object-cover shadow-2xl shadow-slate-300/85"
                            loading="lazy"
                            style={imageStyle}
                          />
                        );
                      })
                    ) : (
                      <div className="absolute inset-x-6 top-4 h-60 rounded-[30px] border border-primary-soft bg-gradient-to-br from-primary-soft to-surface" />
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="mt-10 rounded-3xl border border-primary-soft bg-surface p-6 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-deep">Student Reviews</p>
              <h3 className="mt-1 text-xl font-semibold">
                Review of {reviewSubject} tutors from former students
              </h3>
              <p className="mt-1 text-sm text-muted">
                Feedback from learners and parents after completed lessons.
              </p>
            </div>
            <div className="rounded-full border border-accent/15 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
              4.9 average rating
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
            {STUDENT_REVIEWS.map((review) => (
              <article key={review.name} className="rounded-2xl border border-border bg-surface-2 p-4">
                <Quote className="h-4 w-4 text-accent-light" />
                <p className="mt-2 text-sm leading-6 text-foreground">{review.text}</p>
                <div className="mt-3 flex items-center gap-1 text-accent-light">
                  {Array.from({ length: review.rating }).map((_, idx) => (
                    <Star key={idx} className="h-3.5 w-3.5 fill-current" />
                  ))}
                </div>
                <div className="mt-3 text-sm font-semibold">{review.name}</div>
                <div className="text-xs text-muted">{review.label}</div>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
