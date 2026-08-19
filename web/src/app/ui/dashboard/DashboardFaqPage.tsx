"use client";

import { ChevronDown, CircleHelp, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { PREPVILLA_FAQS } from "./prepvillaFaqs";

export function DashboardFaqPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const categories = useMemo(
    () => ["All", ...Array.from(new Set(PREPVILLA_FAQS.map((item) => item.category)))],
    [],
  );
  const filteredFaqs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return PREPVILLA_FAQS.filter((item) => {
      const matchesCategory = category === "All" || item.category === category;
      const matchesQuery = !normalizedQuery
        || item.question.toLowerCase().includes(normalizedQuery)
        || item.answer.toLowerCase().includes(normalizedQuery)
        || item.category.toLowerCase().includes(normalizedQuery);
      return matchesCategory && matchesQuery;
    });
  }, [category, query]);

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-black/10 bg-[linear-gradient(135deg,var(--palette-navy-deep)_0%,var(--palette-navy)_68%,var(--palette-plum)_100%)] p-6 text-white shadow-[0_24px_48px_rgba(15,23,40,0.2)] sm:p-8">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/10">
            <CircleHelp className="h-6 w-6" />
          </div>
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.16em] text-white/65">Help centre</p>
            <h1 className="mt-1 text-[30px] font-bold leading-tight text-yellow">Frequently asked questions</h1>
            <p className="mt-2 max-w-3xl text-[14px] leading-6 text-white/75">
              Find answers about accounts, tutor discovery, verification, bookings, lessons, payments, payouts, subscriptions, messaging, and support.
            </p>
          </div>
        </div>
        <label className="relative mt-6 block max-w-3xl">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-black/40" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search questions and answers"
            className="h-12 w-full rounded-2xl border border-white/20 bg-white pl-12 pr-4 text-[14px] text-black shadow-sm outline-none placeholder:text-black/40 focus:ring-4 focus:ring-white/20"
          />
        </label>
      </section>

      <div className="flex flex-wrap gap-2" aria-label="FAQ categories">
        {categories.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setCategory(item)}
            className={item === category
              ? "rounded-full bg-primary-deep px-4 py-2 text-[13px] font-semibold text-white"
              : "rounded-full border border-black/10 bg-white px-4 py-2 text-[13px] font-semibold text-primary-deep transition hover:border-black/25"
            }
          >
            {item}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between gap-4">
        <h2 className="text-[18px] font-semibold text-primary-deep">
          {category === "All" ? "All questions" : category}
        </h2>
        <span className="text-[13px] text-black/50">{filteredFaqs.length} result{filteredFaqs.length === 1 ? "" : "s"}</span>
      </div>

      {filteredFaqs.length ? (
        <div className="grid gap-2">
          {filteredFaqs.map((item, index) => (
            <details
              key={`${item.category}-${item.question}`}
              className="group overflow-hidden rounded-2xl border border-black/10 bg-white shadow-[0_10px_24px_rgba(15,23,40,0.04)] open:border-black/20"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 marker:content-none">
                <span>
                  <span className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-black/45">{item.category}</span>
                  <span className="mt-1 block text-[14px] font-semibold leading-6 text-primary-deep">{item.question}</span>
                </span>
                <ChevronDown className="h-5 w-5 shrink-0 text-black/45 transition group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="border-t border-black/8 px-5 py-4 text-[15px] leading-6 text-black/65" id={`faq-answer-${index}`}>
                {item.answer}
              </div>
            </details>
          ))}
        </div>
      ) : (
        <div className="form-panel rounded-2xl p-8 text-center">
          <CircleHelp className="mx-auto h-8 w-8 text-black/35" />
          <h2 className="mt-3 text-[18px] font-semibold text-primary-deep">No matching questions</h2>
          <p className="mt-1 text-[14px] text-black/55">Try a different search term or select another category.</p>
        </div>
      )}
    </div>
  );
}
