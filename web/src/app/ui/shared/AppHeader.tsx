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
    <header
      className={clsx(
        "relative sticky top-0 z-30 border-b backdrop-blur",
        overlay
          ? "border-white/12 bg-background/36 shadow-[0_18px_40px_rgba(15,23,40,0.18)] supports-[backdrop-filter]:bg-background/18"
          : "border-[rgba(23,32,51,0.1)] bg-background/80 shadow-[0_18px_40px_rgba(15,23,40,0.08)] supports-[backdrop-filter]:bg-background/68",
      )}
    >
      {showBackButton ? (
        <button
          type="button"
          onClick={handleBack}
          className="menu-back-button absolute left-1 top-1/2 inline-flex h-16 w-16 -translate-y-1/2 flex-col items-center justify-center rounded-full text-primary-deep focus:outline-none focus:ring-2 focus:ring-accent/60 focus:ring-offset-2 focus:ring-offset-background md:left-2"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="mt-1 text-[11px] font-semibold leading-none">Back</span>
        </button>
      ) : null}
      <div className="mx-auto flex min-h-[var(--app-header-height)] w-full max-w-[1480px] items-center justify-between gap-4 px-4 py-3 md:px-4">
        <div className="flex items-center gap-3">
          <div className={clsx(showBackButton ? "w-16 md:w-20" : "w-0")} aria-hidden="true" />
          <Link
            href="/"
            className={clsx(
              "flex items-center",
              overlay && !showBackButton && "ml-6 md:ml-10",
            )}
          >
            <div
              className={clsx(
                "text-[20px] font-extrabold leading-[24px] tracking-tight md:text-[24px] md:leading-[28px]",
                overlay ? "text-[color:var(--palette-paper)]" : "text-primary-deep",
              )}
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
  );
}
