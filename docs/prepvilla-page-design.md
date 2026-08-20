# PrepVilla Page Design (Desktop-first)

## Global Styles (All Pages)
- Layout system: Flexbox for app shells + CSS Grid for card lists; max-width container (1200px) centered.
- Spacing: 8px scale (8/16/24/32/48); consistent card padding (16–24).
- Color tokens
  - Background: #0B1020 (app shell) / #0F172A (surfaces)
  - Surface: #111C33; Border: rgba(255,255,255,0.08)
  - Text: #E5E7EB; Muted: #9CA3AF
  - Accent: #6366F1; Success: #22C55E; Danger: #EF4444
- Typography: Inter/system; H1 32/40, H2 24/32, H3 18/28, Body 14/22.
- Buttons: primary (accent), secondary (surface), destructive (danger); hover = +8% brightness; focus ring accent.
- Links: accent underline on hover; visited stays accent.
- Responsive (desktop-first):
  - ≥1024px: two-column layouts where applicable
  - 768–1023px: collapse side panels into tabs/drawers
  - <768px: single-column stacked sections; sticky bottom CTA on profile

## Page: About PrepVilla
### Meta Information
- Title: “About PrepVilla”
- Description: “Learn how PrepVilla helps students find trusted tutors and helps teachers build better learning experiences.”

### Page Structure
- Sticky header with the primary marketplace navigation.
- Introductory hero with mission, student/tutor calls to action, and trust markers.
- Content sections covering why PrepVilla exists, who it serves, how learning works, trust principles, and the long-term vision.

### Sections & Components
1. Mission and purpose
   - Explain the verified-teacher marketplace and the need for clearer tutor discovery.
2. Students and tutors
   - Show the distinct value PrepVilla provides to each side of the learning relationship.
3. How it works
   - Discover, communicate, book, and keep making progress.
4. Trust principles and vision
   - Verification, human communication, flexible teaching modes, and a simpler learning journey.

## Page: Home (Find a Tutor)
### Meta Information
- Title: “PrepVilla — Find Verified Teachers”
- Description: “Search verified tutors by subject, price, and availability.”
- OG: title + short description + default share image.

### Page Structure
- Header (sticky): logo, search input, auth CTA (Login/Sign up) or user menu.
- Main: two-column (desktop)
  - Left: Filters panel (collapsible on tablet/mobile)
  - Right: Results list + sorting

### Sections & Components
1. Header
   - Search bar (subject/keyword), timezone selector (optional), “Find Tutors” button.
2. Filters Panel
   - Price range, level, language, availability window, verification toggle.
3. Results
   - TutorCard grid (2–3 columns desktop; 1–2 columns smaller)
   - TutorCard: avatar, name, subjects chips, hourly rate, verification badge, “View profile”.
4. Empty/Loading States
   - Skeleton cards while searching; “No tutors match” guidance.

## Page: Tutor Profile & Booking
### Meta Information
- Title: “{Tutor Name} — Verified Tutor on PrepVilla”
- Description: “View profile, availability, and request a lesson.”
- OG: tutor image, name, headline.

### Page Structure
- Desktop: 2-column
  - Left: profile content
  - Right: booking card (sticky)

### Sections & Components
1. Profile Header
   - Name, headline, verification badge (Approved/Pending), languages, timezone.
2. About + Subjects
   - Bio, subject chips, experience/credentials summary (text-only).
3. Availability Preview
   - Next available slots list; “Request a time range” option.
4. Booking Card (Primary CTA)
   - Slot picker or date/time range inputs, lesson type (dropdown), notes textarea, “Send booking request”.
   - Status feedback after submit (requested/awaiting response).
5. Messaging Entry
   - “Message tutor” opens conversation (modal on desktop; full page on mobile).

## Page: Login & Sign up
### Meta Information
- Title: “Sign in — PrepVilla” / “Create account — PrepVilla”
- Description: “Access your bookings and messages.”

### Page Structure
- Centered auth card on neutral background; optional right-side illustration on desktop.

### Sections & Components
1. Auth Card
   - Tabs: Login / Sign up
   - Inputs: email/phone, password; inline validation; “Forgot password”.
2. Role Selection (Sign up)
   - Student vs Tutor selector with short explanations.
3. Tutor Onboarding Redirect
   - Post-signup banner: “Complete verification to be listed”.

## Page: Dashboard (Student/Tutor)
### Meta Information
- Title: “Dashboard — PrepVilla”
- Description: “Manage bookings, messages, and your profile.”

### Page Structure
- Desktop: left sidebar + main content
  - Sidebar: Bookings, Messages, Profile, (Tutor-only) Availability, Verification
  - Main: routed content with header + breadcrumbs

### Sections & Components
1. Bookings (default view)
   - Status tabs, booking table/cards, booking detail drawer.
   - Actions: cancel (if allowed), confirm/decline (tutor), add notes.
2. Messages
   - Split view: conversation list (left) + chat thread (right).
   - Real-time updates; typing indicator optional; message send bar sticky.
3. Profile
   - Basic info fields; timezone; save CTA.
4. Tutor-only: Availability
   - Calendar/list editor; add slot; prevent overlaps; “Save changes”.
5. Tutor-only: Verification
   - Stepper: submit docs + form; status badge; admin notes if rejected.

## Page: Admin Verification
### Meta Information
- Title: “Admin — Verification”
- Description: “Review and decide tutor verification requests.”

### Page Structure
- Desktop: table list + details panel (split view)

### Sections & Components
1. Queue Table
   - Columns: tutor, submitted date, status, flags; filters by status.
2. Review Panel
   -
