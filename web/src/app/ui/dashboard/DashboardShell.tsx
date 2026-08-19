"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { Bug, CalendarClock, CheckCircle2, CircleAlert, CircleHelp, CreditCard, FileBadge2, Headset, Heart, LayoutDashboard, Lightbulb, MessagesSquare, Settings, ShieldCheck, UserRound, Video } from "lucide-react";
import type { ReactNode } from "react";
import { AppHeader } from "../shared/AppHeader";
import { RequireAuth } from "../shared/RequireAuth";
import { useAuthStore } from "../shared/authStore";

type NavItem = { href: string; label: string; icon: ReactNode; roles: ("student" | "tutor" | "admin")[] };

const items: NavItem[] = [
  { href: "/dashboard/bookings", label: "Bookings", icon: <CheckCircle2 className="h-4 w-4" />, roles: ["student", "tutor", "admin"] },
  { href: "/dashboard/messages", label: "Messages", icon: <MessagesSquare className="h-4 w-4" />, roles: ["student", "tutor", "admin"] },
  { href: "/dashboard/favorites", label: "Favorites", icon: <Heart className="h-4 w-4" />, roles: ["student"] },
  { href: "/dashboard/profile", label: "Profile", icon: <UserRound className="h-4 w-4" />, roles: ["student", "tutor", "admin"] },
  { href: "/dashboard/availability", label: "Availability", icon: <CalendarClock className="h-4 w-4" />, roles: ["tutor"] },
  { href: "/dashboard/video-room", label: "Video Room", icon: <Video className="h-4 w-4" />, roles: ["tutor"] },
  { href: "/dashboard/verification", label: "Verification", icon: <FileBadge2 className="h-4 w-4" />, roles: ["tutor"] },
  { href: "/dashboard/student-verification", label: "Verification", icon: <FileBadge2 className="h-4 w-4" />, roles: ["student"] },
  { href: "/dashboard/support", label: "Support", icon: <Headset className="h-4 w-4" />, roles: ["tutor"] },
  { href: "/dashboard/feedback", label: "Feedback", icon: <Lightbulb className="h-4 w-4" />, roles: ["student", "tutor"] },
  { href: "/dashboard/complaint", label: "Complaint", icon: <CircleAlert className="h-4 w-4" />, roles: ["student", "tutor"] },
  { href: "/dashboard/issues", label: "Issues", icon: <Bug className="h-4 w-4" />, roles: ["student", "tutor"] },
  { href: "/dashboard/faq", label: "FAQ", icon: <CircleHelp className="h-4 w-4" />, roles: ["student", "tutor"] },
  { href: "/dashboard/billing", label: "Billing & Subscription", icon: <CreditCard className="h-4 w-4" />, roles: ["student", "tutor"] },
  { href: "/dashboard/settings", label: "Settings", icon: <Settings className="h-4 w-4" />, roles: ["student", "tutor"] },
  { href: "/admin/verification", label: "Admin", icon: <ShieldCheck className="h-4 w-4" />, roles: ["admin"] },
];

export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const role = useAuthStore((s) => s.role);
  const displayName = useAuthStore((s) => s.displayName);
  const roleKey: "student" | "tutor" | "admin" | null = role ? ((role as string).toLowerCase() === "teacher" ? "tutor" : (role as string).toLowerCase() as "student" | "tutor" | "admin") : null;
  const firstName = displayName?.trim().split(/\s+/)[0] || "";

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="mx-auto grid w-full max-w-[1500px] grid-cols-1 gap-6 px-4 pb-10 pt-6 lg:grid-cols-[260px_1fr]">
          {firstName && (roleKey === "student" || roleKey === "tutor") ? (
            <div className="lg:col-span-2">
              <p className="text-[14px] font-medium leading-[22px] text-black/60">Welcome</p>
              <p className="brand-heading text-[24px] font-semibold leading-[32px] text-primary-deep">{firstName}</p>
            </div>
          ) : null}
          <aside className="menu-surface rounded-[28px] p-3">
            <div className="mb-8 flex items-center gap-2 px-2 py-2 text-[18px] font-semibold leading-[28px] text-primary-deep">
              <LayoutDashboard className="h-6 w-6" />
              Dashboard
            </div>
            <nav className="mt-4 grid gap-2">
              {items
                .filter((it) => (roleKey ? it.roles.includes(roleKey) : false))
                .map((it) => (
                  <Link
                    key={it.href}
                    href={it.href}
                    aria-current={isActive(it.href) ? "page" : undefined}
                    className={clsx(
                      "mb-0.7 menu-link flex items-center gap-2 rounded-2xl px-3 py-2.5 text-[14px] font-semibold leading-[22px]",
                      isActive(it.href) ? "menu-link-active" : "text-primary-deep",
                    )}
                  >
                    {it.icon}
                    {it.label}
                  </Link>
                ))}
            </nav>
          </aside>
          <section className="min-w-0">{children}</section>
        </main>
      </div>
    </RequireAuth>
  );
}
