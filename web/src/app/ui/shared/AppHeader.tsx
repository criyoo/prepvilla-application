"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { clsx } from "clsx";
import { ArrowLeft, BookOpenCheck, Info, LogOut, Search, UserRound } from "lucide-react";
import { Button } from "./Button";
import { useAuthStore } from "./authStore";

type AppHeaderProps = {
  hideMenu?: boolean;
  hideActions?: boolean;
  overlay?: boolean;
};

export function AppHeader({ hideMenu = false, hideActions = false, overlay = false }: AppHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { role, displayName, clear, loadFromStorage } = useAuthStore();
  const resolvedDisplayName = displayName?.trim() || null;
  const showBackButton = pathname !== "/";
  const searchActive = pathname.startsWith("/search");
  const aboutActive = pathname.startsWith("/about");
  const howItWorksActive = pathname.startsWith("/how-it-works");
  const dashboardActive = pathname.startsWith("/dashboard") || pathname.startsWith("/admin");
  const loginActive = pathname === "/login";
  const signupActive = pathname.startsWith("/signup");
  const dashboardHref =
    role === "student" ? "/dashboard/profile" : role === "tutor" ? "/dashboard/verification" : "/dashboard";
  const dashboardLabel =
    role === "student"
      ? `${resolvedDisplayName ?? "Student"} Dashboard`
      : role === "tutor"
        ? `${resolvedDisplayName ?? "Tutor"} Dashboard`
        : role === "admin"
          ? `${resolvedDisplayName ?? "Admin"} Dashboard`
          : (resolvedDisplayName ?? "Dashboard");
  const menuButtonClassName = "h-7 gap-1.8 rounded-x2 px-3 text-[12px] leading-none";
  const menuIconClassName = "h-3.5 w-3.5";

  function prefetchRoute(href: string) {
    void router.prefetch(href);
  }

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  function handleBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/");
  }

  return (
    <>
      <header
        className={clsx(
          "relative sticky top-0 z-10 bg-transparent",
          overlay
            ? "shadow-[0_10px_10px_-34px_rgba(15,23,40,0.18)]"
            : "shadow-[0_10px_10px_-34px_rgba(15,23,40,0.18)]",
        )}
      >
        <div className="mx-auto flex min-h-[var(--app-header-height)] w-full max-w-[1480px] items-center justify-between gap-4 px-4 py-3 md:px-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center">
              <div
                className="brand-logo text-[20px] font-extrabold leading-[24px] tracking-tight md:text-[24px] md:leading-[28px]"
              >
                PrepVilla
              </div>
            </Link>
          </div>

          {!hideActions ? (
            <div className="flex items-center gap-1.5">
              {!hideMenu ? (
                <Link href="/about" onMouseEnter={() => prefetchRoute("/about")} onFocus={() => prefetchRoute("/about")}>
                  <Button variant={aboutActive ? "menuActive" : "menu"} className={menuButtonClassName}>
                    <Info className={menuIconClassName} />
                    <span>About</span>
                  </Button>
                </Link>
              ) : null}

              {!hideMenu ? (
                <Link className="hidden lg:block" href="/how-it-works" onMouseEnter={() => prefetchRoute("/how-it-works")} onFocus={() => prefetchRoute("/how-it-works")}>
                  <Button variant={howItWorksActive ? "menuActive" : "menu"} className={menuButtonClassName}>
                    <BookOpenCheck className={menuIconClassName} />
                    <span className="hidden md:inline">How it works</span>
                    <span className="md:hidden">How</span>
                  </Button>
                </Link>
              ) : null}

              {!hideMenu ? (
                <Link href="/search" onMouseEnter={() => prefetchRoute("/search")} onFocus={() => prefetchRoute("/search")}>
                  <Button variant={searchActive ? "menuActive" : "menu"} className={menuButtonClassName}>
                    <Search className={menuIconClassName} />
                    <span className="hidden sm:inline">Find a tutor</span>
                    <span className="sm:hidden">Find</span>
                  </Button>
                </Link>
              ) : null}

              {role ? (
                <>
                  <Link href={dashboardHref} onMouseEnter={() => prefetchRoute(dashboardHref)} onFocus={() => prefetchRoute(dashboardHref)}>
                    <Button variant={dashboardActive ? "menuActive" : "menu"} className={menuButtonClassName}>
                      <UserRound className={menuIconClassName} />
                      <span className="hidden sm:inline">{dashboardLabel}</span>
                      <span className="sm:hidden">Dash</span>
                    </Button>
                  </Link>
                  <Button variant="menu" onClick={clear} className={menuButtonClassName}>
                    <LogOut className={menuIconClassName} />
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Link href="/signup/tutor" onMouseEnter={() => prefetchRoute("/signup/tutor")} onFocus={() => prefetchRoute("/signup/tutor")}>
                    <Button variant={signupActive ? "menuActive" : "menu"} className={menuButtonClassName}>
                      Become a tutor
                    </Button>
                  </Link>
                  <Link href="/login" onMouseEnter={() => prefetchRoute("/login")} onFocus={() => prefetchRoute("/login")}>
                    <Button variant={loginActive ? "menuActive" : "menu"} className={menuButtonClassName}>
                      Login
                    </Button>
                  </Link>
                </>
              )}
            </div>
          ) : null}
        </div>
      </header>
      {showBackButton ? (
        <div className="pointer-events-none absolute left-0 top-[var(--app-header-height)] z-20 w-full">
          <div className="mx-auto w-full max-w-[1480px] px-4 pt-3">
            <button
              type="button"
              onClick={handleBack}
              className="menu-back-button pointer-events-auto inline-flex h-10 items-center gap-2 rounded-xl border border-black/10 bg-white/90 px-3.5 text-[13px] font-semibold text-primary-deep shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-[rgba(139,97,120,0.36)] hover:bg-[var(--secondary-color-soft)] focus:outline-none focus:ring-2 focus:ring-accent/60 focus:ring-offset-2 focus:ring-offset-background"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back</span>
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
