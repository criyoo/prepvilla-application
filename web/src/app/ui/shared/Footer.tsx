import Link from "next/link";
import type { SVGProps } from "react";
import {
  ArrowRight,
  BadgeCheck,
  BookOpenCheck,
  CalendarCheck2,
  GraduationCap,
  Instagram,
  Linkedin,
  Mail,
  MapPin,
  MessageCircle,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import BrandLogo from "./BrandLogo";

const browseLinks = [
  { label: "Home", href: "/" },
  { label: "About PrepVilla", href: "/about" },
  { label: "Find a tutor", href: "/search" },
  { label: "How it works", href: "/how-it-works" },
];

const footerHighlights = [
  {
    label: "Verified profiles",
    description: "See the details that help you choose a tutor with confidence.",
    icon: BadgeCheck,
  },
  {
    label: "Direct conversations",
    description: "Ask questions and keep your learning conversations organized.",
    icon: MessageCircle,
  },
  {
    label: "Flexible learning",
    description: "Find online or face-to-face lessons that fit real schedules.",
    icon: CalendarCheck2,
  },
];

const accountLinks = [
  { label: "Log in", href: "/login" },
  { label: "Create account", href: "/signup" },
  { label: "Dashboard", href: "/dashboard" },
  { label: "Saved tutors", href: "/dashboard/favorites" },
];

const socialLinks = [
  { label: "X", href: "https://x.com/Prepvilla", icon: XIcon },
  { label: "LinkedIn", href: "https://www.linkedin.com/in/prepvilla", icon: Linkedin },
  { label: "Instagram", href: "https://www.instagram.com/prepvilla", icon: Instagram },
];

export function Footer() {
  const tutorLinks = [
    { label: "Become a tutor", href: "/signup/tutor" },
    { label: "Tutor verification", href: "/signup/tutor" },
    { label: "Tutor dashboard", href: "/dashboard/verification" },
    { label: "About PrepVilla", href: "/about" },
  ];

  return (
    <footer className="border-t border-[rgba(255,255,255,0.08)] bg-primary-deep text-white">
      <div className="bg-[linear-gradient(135deg,rgba(240,100,73,0.16),rgba(15,23,40,0)_42%,rgba(139,97,120,0.2))]">
        <div className="mx-auto max-w-[1480px] px-5 py-12 sm:px-8 lg:px-10 lg:py-16">
          <div className="grid gap-12 border-b border-white/10 pb-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.35fr)]">
            <div className="flex h-full flex-col gap-6">
              <Link href="/" aria-label="PrepVilla home" className="inline-flex w-fit items-center gap-3 text-white">
                <BrandLogo className="h-24 w-24 w-auto" />
              </Link>

              <div className="space-y-3">
                <p className="max-w-xl text-lg font-semibold leading-7 text-white sm:text-xl">
                  Find trusted tutors and build a learning journey that works for you.
                </p>
                <p className="max-w-xl text-sm leading-6 text-white/65">
                  PrepVilla brings students and tutors together with clearer profiles, meaningful conversations, and flexible lesson planning.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Link href="/search" className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-black/20 transition hover:-translate-y-0.5 hover:bg-accent-hover">
                  Find a tutor
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a href="mailto:support@prepvilla.info" className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-sm font-semibold text-white/85 transition hover:border-white/30 hover:bg-white/10 hover:text-white">
                  <Mail className="h-4 w-4 text-accent-light" />
                  Contact support
                </a>
              </div>

              <div className="mt-auto grid gap-3 sm:grid-cols-3">
                {footerHighlights.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.label} className="flex min-h-36 flex-col rounded-2xl border border-white/10 bg-white/5 p-4">
                      <span className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl bg-accent/15 text-accent-light">
                        <Icon className="h-5 w-5" />
                      </span>
                      <p className="text-sm font-semibold text-white">{item.label}</p>
                      <p className="mt-auto pt-2 text-sm leading-5 text-white/60">{item.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="grid items-start gap-10 sm:grid-cols-2 xl:grid-cols-3">
              <FooterNav title="Explore" links={browseLinks} />
              <FooterNav title="Account" links={accountLinks} />
              <FooterNav title="For tutors" links={tutorLinks} />

              <div className="sm:col-span-2 xl:col-span-3">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent-light">Support</p>
                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <a href="mailto:support@prepvilla.info" className="flex min-h-32 flex-col rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/65 transition hover:border-accent/40 hover:bg-white/10">
                    <Mail className="h-5 w-5 text-accent-light" />
                    <span className="mt-auto block">
                      <span className="block font-semibold text-white">Email support</span>
                      <span className="mt-1 block">support@prepvilla.info</span>
                    </span>
                  </a>
                  <div className="flex min-h-32 flex-col rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/65">
                    <MapPin className="h-5 w-5 text-accent-light" />
                    <span className="mt-auto block">
                      <span className="block font-semibold text-white">Built for Nigeria</span>
                      <span className="mt-1 block">Learn online or face-to-face across the country.</span>
                    </span>
                  </div>
                  <Link href="/how-it-works" className="flex min-h-32 flex-col rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/65 transition hover:border-accent/40 hover:bg-white/10">
                    <BookOpenCheck className="h-5 w-5 text-accent-light" />
                    <span className="mt-auto block">
                      <span className="block font-semibold text-white">Learn how it works</span>
                      <span className="mt-1 block">Discover, compare, connect, and keep progressing.</span>
                    </span>
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-5 pt-6 text-sm text-white/50 xl:flex-row xl:items-center xl:justify-between">
            <p>Copyright {new Date().getFullYear()} PrepVilla. All rights reserved.</p>
            <nav aria-label="Social media" className="flex items-center gap-3">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-white/50">Follow us</span>
              <div className="flex items-center gap-2">
                {socialLinks.map((socialLink) => {
                  const Icon = socialLink.icon;
                  return (
                    <a
                      key={socialLink.label}
                      href={socialLink.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`PrepVilla on ${socialLink.label}`}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white/65 transition hover:border-accent/50 hover:bg-accent/15 hover:text-white"
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </a>
                  );
                })}
              </div>
            </nav>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <span className="inline-flex items-center gap-2"><BadgeCheck className="h-4 w-4 text-accent-light" /> Trusted tutor details</span>
              <span className="inline-flex items-center gap-2"><UsersRound className="h-4 w-4 text-accent-light" /> Students and tutors together</span>
              <span className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-accent-light" /> Learning with clarity</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

function XIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.657l-5.214-6.817-5.967 6.817H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z" />
    </svg>
  );
}

function FooterNav({ title, links }: { title: string; links: { label: string; href: string }[] }) {
  return (
    <nav aria-label={title}>
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-accent-light">{title}</p>
      <ul className="mt-4 space-y-3 text-sm text-white/65">
        {links.map((link) => (
          <li key={`${title}-${link.label}`}>
            <Link className="transition hover:text-white" href={link.href}>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
