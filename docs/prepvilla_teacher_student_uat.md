# PrepVilla Teacher and Student User Acceptance Test

Product: PrepVilla verified-teacher marketplace  
Application reviewed: `/Users/chris/Developer/Projects/serverbased/prepvilla/apps`  
Prepared date: 2026-08-24  
Execution status values: Not Run, Pass, Fail, Blocked, Retest Pass  
Roles in this document: Teacher means the application's Tutor role; Student means the Student role.

## Purpose

This document provides business-readable User Acceptance Test scripts for the complete PrepVilla teacher and student experience. It covers the implemented web journeys and their supporting business rules, including authentication, automated identity verification, tutor discovery, profiles, availability, favorites, bookings, messaging, lesson payment and completion, reviews, video rooms, subscriptions, support, account security, permissions, responsive behavior, and recovery states.

## Scope and traceability

| Area | Teacher coverage | Student coverage | Shared or cross-role coverage |
| --- | --- | --- | --- |
| Public site and authentication | PV-COM-001 to PV-COM-010 | PV-COM-001 to PV-COM-010 | PV-COM-001 to PV-COM-010 |
| Identity verification and profile | PV-TCH-002 to PV-TCH-011 | PV-STU-002 to PV-STU-008 | PV-XRL-007 |
| Discovery and favorites | PV-TCH-010 to PV-TCH-012 | PV-STU-009 to PV-STU-014 | PV-XRL-001 |
| Availability and bookings | PV-TCH-013 to PV-TCH-020 | PV-STU-015 to PV-STU-022 | PV-XRL-001 to PV-XRL-004 |
| Messaging and video lessons | PV-TCH-021 to PV-TCH-024 | PV-STU-023 to PV-STU-025 | PV-XRL-001, PV-XRL-002, PV-XRL-004 |
| Billing and subscriptions | PV-TCH-025 | PV-STU-026 | PV-XRL-003 |
| Support, FAQ, and settings | PV-TCH-026 to PV-TCH-030 | PV-STU-027 to PV-STU-031 | PV-XRL-007 |
| Quality, privacy, and resilience | PV-XRL-005 to PV-XRL-008 | PV-XRL-005 to PV-XRL-008 | PV-XRL-005 to PV-XRL-008 |

## Assumptions and entry criteria

- The target UAT environment is available and points to the intended PrepVilla API, database, media storage, email service, WebSocket service, verification providers, Flutterwave sandbox, and Jitsi configuration.
- Testers have separate, valid email inboxes for teacher and student accounts, plus access to all six-character OTP messages.
- Test NIN, BVN, mobile, biodata, bank, identity, qualification, and address data are approved for test use and match the configured verification sandbox.
- At least one approved and publicly listed teacher offers face-to-face and webcam lessons, has future availability, and has a valid hourly rate.
- At least one verified student and one approved teacher are available for cross-role booking, chat, payment, completion, review, and video-room testing.
- Clear profile photos and identity/qualification documents are available in accepted image or PDF formats. Oversized, unsupported, and corrupt files are also available for negative tests.
- Payment-provider test cards and callback scenarios are available for success, cancellation, failure, duplicate callback, and delayed confirmation.
- Testers can capture screenshots, OTP timestamps, booking/payment references, video-room links, and email confirmations as evidence.

## Execution rules

- Mark each UAT case as Not Run, Pass, Fail, Blocked, or Retest Pass.
- Record the tester, date, environment/build, actual result, evidence link, and defect ID for every executed case.
- Use a new account or reset test data where a one-time rule is involved, such as the free package or OTP attempt limit.
- Do not use real personal identity documents, real bank details, or live payment cards.
- Any Critical or High failure in authentication, identity verification, authorization, booking, payment, lesson completion, privacy, or account deletion blocks sign-off until fixed and retested.
- A visible feature that cannot be reached by its intended role must be marked Fail, even if the supporting API exists.

## Common authentication and navigation tests

### PV-COM-001 - Public pages and primary navigation

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm logged-out visitors can understand PrepVilla and reach the main entry points.

Preconditions / test data: Tester is logged out.

Steps:

1. Open `/`, `/about`, `/how-it-works`, `/search`, and `/tutors`.
2. Use the header and footer links for About, How It Works, Find Tutors, Login, Student sign-up, Become a Tutor, support email, and social links.
3. Use the browser Back button from a secondary page.
4. Open an unknown tutor profile URL.

Expected result: Public pages load without authentication errors; links route correctly; the active navigation state is clear; Back works; an unknown tutor shows a useful not-found/error state without exposing technical details.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-002 - Create a student account and request OTP

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a new student can submit a valid registration.

Preconditions / test data: Unique student email; password of at least six characters.

Steps:

1. Open `/signup`.
2. Enter full name, email, password, and matching confirmation.
3. Submit the form.
4. Check the target inbox.

Expected result: Required-field and matching-password checks pass; the Verify Email screen shows the target address; exactly one valid six-character OTP is delivered; the account is not usable until verification.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-003 - Create a teacher account and request OTP

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a new teacher can enter the tutor onboarding path.

Preconditions / test data: Unique teacher email; password of at least six characters.

Steps:

1. Open `/signup/tutor`.
2. Enter first name, optional middle name, last name, email, and password.
3. Submit the form and check the inbox.

Expected result: First and last name are mandatory; the full name is composed correctly; a six-character OTP is sent; the page moves to email verification.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-004 - Verify registration OTP and use resend

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm correct OTP use and resend behavior for both roles.

Preconditions / test data: One pending student registration and one pending teacher registration.

Steps:

1. Request a resend and observe its cooldown/disabled state.
2. Confirm a replacement OTP is delivered.
3. Enter the valid OTP for each role.
4. Observe the destination and try reusing the same OTP.

Expected result: Resend is rate-controlled; the newest OTP verifies once; reused codes fail; the teacher is authenticated and routed to verification; the student is routed to Login with an Email verified notice.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-005 - Reject invalid, expired, and over-attempted OTPs

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm account verification cannot be bypassed.

Preconditions / test data: Pending registration; wrong, expired, and malformed codes.

Steps:

1. Submit fewer or more than six characters.
2. Submit an incorrect six-character code repeatedly.
3. Make the sixth attempt after five failed attempts.
4. Submit an expired code, then request a new code and use it.

Expected result: Malformed, wrong, and expired codes are rejected; the account remains unverified; five failures trigger a clear too-many-attempts response; a newly issued code can complete verification.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-006 - Google sign-up and sign-in

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm Google authentication respects mode, role, verification, and safe redirect rules.

Preconditions / test data: Verified Google email; existing and new PrepVilla test accounts.

Steps:

1. Sign up as Student with Google.
2. Sign up as Teacher with a different Google account.
3. Sign in with Google using an existing account.
4. Try to register an existing email under the opposite role.
5. Cancel the Google popup and test an invalid/expired authorization session.

Expected result: Accounts retain the selected role; verified Google email is required; existing-email role mismatch is rejected; cancellation and configuration errors are readable; safe in-app redirects work without allowing an external redirect.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-007 - Login and role-specific landing route

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm verified users receive the correct authenticated experience.

Preconditions / test data: Verified student and teacher accounts.

Steps:

1. Log in as Student with email/password.
2. Log out, then log in as Teacher.
3. Repeat from a protected URL containing a valid `next` path.

Expected result: Credentials establish the correct role session; Student and Teacher land on their intended dashboard/onboarding page; a safe `next` path is honored; role-specific navigation is shown.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-008 - Login validation, unverified account, and frozen account state

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm invalid or restricted account states do not receive normal access.

Preconditions / test data: Wrong password, unknown email, unverified account, and frozen teacher account.

Steps:

1. Submit blank and malformed login fields.
2. Try an unknown email and wrong password.
3. Try a correct password for an unverified account.
4. Sign in to a frozen teacher account and attempt a protected marketplace action.

Expected result: Errors do not reveal whether an account exists except for the explicit unverified state; unverified users are denied; frozen-account restrictions and status are clear and business actions remain unavailable until unfreezing/expiry.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-009 - Forgot-password recovery

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm secure password recovery for either role.

Preconditions / test data: Registered email plus unknown email; access to the registered inbox.

Steps:

1. Request a reset for the registered email and for an unknown email.
2. Confirm the response does not disclose account existence.
3. Enter mismatched/short passwords and an invalid code.
4. Use the valid code with matching password, then try to reuse it.
5. Log in with the old and new passwords.

Expected result: A valid account receives a reset code; unknown-email response is neutral; password rules apply; invalid/reused/expired codes fail; only the new password works after success.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-COM-010 - Session refresh, protected routes, role boundaries, and logout

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm session continuity and authorization boundaries.

Preconditions / test data: Student and Teacher accounts; an expired access token with valid refresh token.

Steps:

1. Open dashboard pages while logged out.
2. Sign in, expire the access token, and perform a normal read action.
3. As Student, open teacher-only Availability, Support, and Verification routes.
4. As Teacher, open Student Favorites and Student Verification routes.
5. Log out and use Back/refresh on a protected page.

Expected result: Logged-out users return to Login with a safe `next` path; token refresh is transparent and does not duplicate requests; wrong-role pages redirect or deny access; logout clears stored credentials and protected content cannot be recovered through Back/refresh.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

## Student tests

### PV-STU-001 - Student dashboard and navigation

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the student sees only the student workspace.

Preconditions / test data: Logged-in student.

Steps:

1. Open `/dashboard` and use the sidebar/header.
2. Visit Billing, Bookings, Messages, Favorites, Profile, Verification, Feedback, Issues, Complaint, FAQ, and Settings.
3. Confirm the selected menu item updates.

Expected result: Every student page loads; teacher-only items are absent; identity and role remain consistent; navigation works on refresh and direct links.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-002 - Student verification form loads and preserves a draft

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm verification data can be entered safely without accidental loss.

Preconditions / test data: Unverified student.

Steps:

1. Open Student Verification.
2. Enter partial biodata, origin, qualification, residence, NIN/BVN, and notes.
3. Navigate away and return or refresh.
4. Compare restored fields; verify email is read-only.

Expected result: Authenticated email and existing profile data are prefilled; partial form values are restored for the same user only; another account cannot see the draft.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-003 - Submit student verification with NIN only

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm BVN is optional for students and NIN verification can complete onboarding.

Preconditions / test data: Matching student biodata, linked Nigerian mobile, valid 11-digit NIN, clear photo, ID document, and qualification document.

Steps:

1. Complete first/middle/last name, date of birth, country/nationality, state/LGA of origin, qualification, residence, and mobile.
2. Enter valid NIN and leave BVN blank.
3. Upload the required photo and both documents.
4. Submit.

Expected result: BVN is treated as optional; files upload; NIN data is verified; status becomes Approved; confirmation appears and is emailed; profile data is synchronized; the student can contact tutors and book lessons.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-004 - Submit student verification with NIN and BVN

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm optional BVN is validated when provided.

Preconditions / test data: Matching biodata, 11-digit NIN and BVN, and required uploads.

Steps:

1. Complete all verification fields.
2. Enter valid NIN and BVN.
3. Submit and refresh the status page.

Expected result: NIN and BVN are both verified against submitted biodata; success data persists; status and decision date are visible; sensitive raw provider payload is not shown.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-005 - Reject incomplete or malformed student verification

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm required student identity data cannot be skipped.

Preconditions / test data: Student verification form.

Steps:

1. Submit with required fields blank.
2. Enter invalid mobile, non-11-digit NIN, and a malformed optional BVN.
3. Use an invalid date and change the read-only account email.
4. Omit the photo, ID document, then qualification document in separate attempts.
5. Select a Nigerian origin without state/LGA and a non-Nigerian origin without region values.

Expected result: Submission stays blocked; each problem has a readable field or summary error; no Approved record is created; entered safe values remain available for correction.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-006 - Handle verification mismatch and provider outage

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm verification failure is safe and actionable.

Preconditions / test data: Mismatching biodata/NIN; configured provider outage simulation.

Steps:

1. Submit identity data that does not match the NIN/BVN record.
2. Retry during verification-provider unavailability.
3. Correct the data and resubmit after service recovery.

Expected result: Mismatch is rejected without approval; provider outage shows a temporary-service error rather than a false rejection; no duplicate request is created; corrected data can succeed later.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-007 - Approved student verification is locked

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm verified identity data cannot be casually altered.

Preconditions / test data: Approved student.

Steps:

1. Reopen Verification after approval.
2. Try to change fields or replace files.
3. Refresh and follow the automatic Profile redirect.

Expected result: Status shows Approved; protected fields and file controls are disabled; Submit shows Verification Complete; the redirect occurs once without a loop; supported changes are directed to Settings or Support.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-008 - Update student profile and photo

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm allowed student profile fields persist.

Preconditions / test data: Verified student; valid image and invalid upload samples.

Steps:

1. Open Profile and edit allowed display/profile/location fields.
2. Upload a valid profile photo and save.
3. Refresh and sign out/in.
4. Try an unsupported or oversized photo and attempt to change a secured address directly.

Expected result: Allowed data and photo persist; upload errors are readable; email remains read-only; secured address changes require Settings OTP; saved identity data stays consistent with verification.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-009 - Search tutors by category and subject

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm subject discovery returns relevant approved tutors.

Preconditions / test data: Listed tutors across multiple subject categories.

Steps:

1. Open Search from Home and select featured subject chips.
2. Select a Subject Category and a known Subject.
3. Enter Other Subject.
4. Use legacy/search query URL parameters and refresh.

Expected result: Results match the selected category/subject; dependent subject options update; URL state is normalized and restorable; only approved listed tutors appear.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-010 - Apply location and teacher-attribute filters

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm advanced filters narrow results correctly.

Preconditions / test data: Tutors with varied state/city, rate, qualification, gender, and language.

Steps:

1. Filter by State and dependent City, including Other Location.
2. Set minimum and maximum hourly rate.
3. Filter by qualification, gender, and language.
4. Combine all filters, then remove them one by one.

Expected result: Each filter and combination returns only matching tutors; city options follow state; rate boundaries are inclusive; removing a filter updates results without stale values.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-011 - Reset filters, paginate results, and handle empty/error states

Priority: Medium  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm search remains understandable across result states.

Preconditions / test data: More than 15 matching tutors; query with no matches; simulated API error.

Steps:

1. Apply filters and use Next/Previous pagination.
2. Change a filter while on a later page.
3. Search for a non-existent subject/location.
4. Reset filters.
5. Retry after a load failure.

Expected result: Fifteen results or fewer appear per page; paging bounds are respected; filter changes return to page one; no-results guidance is clear; Reset clears URL and controls; load errors do not show stale results.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-012 - Review tutor cards

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm tutor cards support informed selection.

Preconditions / test data: Approved tutors with/without photo, reviews, free-first-lesson, and both teaching methods.

Steps:

1. Inspect cards on Home, Search, and Favorites.
2. Compare name, headline, subjects, location, rate, rating count, badge, methods, free lesson, and photo fallback.
3. Open a card by mouse and keyboard.

Expected result: Card data matches the tutor profile; verified status is trustworthy; missing images use a stable fallback; keyboard activation opens the correct profile; no private identity data appears.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-013 - View tutor profile, availability, and reviews

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the public tutor profile contains accurate booking information.

Preconditions / test data: Approved listed tutor with future slots and reviews.

Steps:

1. Open the tutor profile.
2. Compare rate, rating, location/timezone, languages, headline, bio, subjects, response time, methods, free lesson, and photo with the teacher's saved profile.
3. Review up to six future availability slots and the empty-availability state.
4. Review ratings, comments, author, and dates.

Expected result: Public data is accurate and readable; only future slots appear in local display time; review totals/average match visible records; empty and load-error states are useful.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-014 - Add, persist, and remove favorite teachers

Priority: Medium  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm favorites belong only to the student.

Preconditions / test data: Logged-out visitor, Student A, Student B, and one listed tutor.

Steps:

1. As logged out, inspect the favorite action.
2. As Student A, favorite from Home/Search and open Favorites.
3. Refresh and sign out/in.
4. Confirm Student B does not inherit it.
5. Remove it from the card/Favorites page.

Expected result: Only authenticated students can favorite; the state persists for Student A only; duplicate adds create one item; removal updates all views and the empty state.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-015 - Block unverified student booking and messaging

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm identity verification gates contact and booking.

Preconditions / test data: Logged-out user, unverified student, approved teacher profile.

Steps:

1. Logged out, click Send booking request and Message tutor.
2. As an unverified student, repeat both actions and open Messages directly.
3. As a teacher account, open another teacher's profile and try both actions.

Expected result: Logged-out users are directed to Student sign-up/login with return path; unverified students receive a verification requirement; teachers cannot start student actions; no booking/conversation is created.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-016 - Request a booking from a published availability slot

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a verified student can request an advertised slot.

Preconditions / test data: Verified student; listed teacher with a future slot and face-to-face method.

Steps:

1. Select Face-to-face and a future slot.
2. Enter learning goals/notes.
3. Send the request.
4. Open Bookings and Messages.

Expected result: One Requested booking is created with correct teacher, method, times, and notes; success guidance appears; an associated conversation exists; notes appear as the initial message once.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-017 - Request a custom future time range

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm booking works when no public slot fits.

Preconditions / test data: Verified student and listed teacher.

Steps:

1. Leave availability unselected.
2. Enter a future From and To range plus notes.
3. Submit and inspect the teacher/student booking records.
4. Try missing endpoint, past start, end before start, and an unavailable/deleted slot.

Expected result: Valid range creates one Requested booking with preserved range; invalid/past/reversed/missing data and unavailable slots are rejected without creating a booking.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-018 - Enforce teacher teaching methods

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm students can request only methods the teacher offers.

Preconditions / test data: One face-to-face-only teacher, one webcam-only teacher, one offering both.

Steps:

1. Open each profile and compare visible method choices.
2. Request each allowed method.
3. Attempt an unsupported method through a stale page/request.

Expected result: UI shows only configured methods; a valid method is saved to the booking; unsupported method is rejected server-side; webcam choice explains video-room availability.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-019 - Start and continue a teacher conversation

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm verified students can communicate with listed teachers.

Preconditions / test data: Verified student and listed teacher.

Steps:

1. Click Message tutor twice from the same profile.
2. Confirm the same conversation opens in Messages.
3. Send text with leading/trailing whitespace and send another message after refresh.
4. Try a blank message.

Expected result: Only one conversation exists for the pair; nonblank messages are trimmed, ordered, timestamped, and visible to both participants; blank messages are blocked.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-020 - Real-time chat, fallback, draft, and access isolation

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm chat works securely with and without WebSocket connectivity.

Preconditions / test data: Student/teacher conversation; second student account; WebSocket interruption control.

Steps:

1. Exchange messages while both users are online.
2. Disconnect WebSocket and wait for polling fallback/reconnect.
3. Type an unsent draft, switch conversations, then return.
4. As Student B, attempt to open Student A's conversation URL.

Expected result: Messages arrive once and in order; reconnect/fallback merges without duplicates; draft is isolated by user and conversation; nonparticipants receive not-found/denied response; tokens are not exposed in page text or logs.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-021 - Review student booking list and statuses

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a student can track every booking state.

Preconditions / test data: Requested, Confirmed, Completed, Rejected, and Cancelled bookings.

Steps:

1. Open Bookings and inspect teacher photo/name, status, schedule/range, method, and notes.
2. Use All and each status tab.
3. Refresh after the teacher accepts/rejects.

Expected result: Newest bookings display correctly; each tab shows only its status; updates appear after refresh; action buttons reflect the current state and role.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-022 - Cancel a student booking

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the student can cancel only eligible own bookings.

Preconditions / test data: Student's Requested and Confirmed bookings; another student's booking; terminal bookings.

Steps:

1. Cancel the Requested booking, then the Confirmed booking.
2. Try to cancel each again.
3. Attempt to cancel another student's booking.
4. Inspect Completed and Rejected bookings.

Expected result: Eligible own bookings become Cancelled; terminal/duplicate/foreign actions are unavailable or denied; no unrelated booking changes.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-023 - Rejected booking blocks conversation

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a teacher rejection closes the related communication channel.

Preconditions / test data: Requested booking with active student-teacher conversation.

Steps:

1. Have the teacher reject the booking.
2. Refresh Student Bookings and Messages.
3. Try to read/send through the blocked thread and direct message endpoint.

Expected result: Booking shows Rejected; conversation is visibly blocked; the composer and real-time connection do not permit new messages; prior history remains appropriately visible without leaking data.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-024 - Pay for a confirmed lesson and handle checkout outcomes

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the student can reach and complete the lesson-payment workflow required before completion.

Preconditions / test data: Confirmed booking, teacher hourly rate, Flutterwave sandbox success/cancel/failure scenarios.

Steps:

1. Open the confirmed booking and start lesson payment.
2. Verify displayed teacher, booking, amount, currency, and transaction reference.
3. Complete a successful checkout and return through the callback.
4. Repeat with cancellation/failure/delayed confirmation and try to start a duplicate payment.

Expected result: A visible student action starts checkout for the correct amount; success is verified before marking payment complete; cancelled/failed/pending states are clear and retryable; duplicate completed/open payments are prevented. If no user-facing payment entry exists, mark this test Fail because lesson completion requires payment.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-025 - Confirm lesson completion and submit a review

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm completion and review rules protect payout and reputation.

Preconditions / test data: Confirmed paid booking that has ended; a future, unpaid, and already-reviewed booking.

Steps:

1. Try completion before lesson end and before payment.
2. After payment/end, confirm completion as Student.
3. Have Teacher confirm and observe final Completed state.
4. Submit a 1-5 rating and comment from the tutor profile.
5. Try invalid rating, foreign booking, pre-completion, and duplicate review.

Expected result: Early/unpaid completion is blocked; each participant confirms once; final status requires both confirmations; eligible review appears once in totals/average; invalid, foreign, early, and duplicate reviews are rejected.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-026 - Student subscription packages and billing history

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm student subscription selection and payment records are accurate.

Preconditions / test data: New student; payment success/cancel/fail scenarios.

Steps:

1. Open Billing and compare Free, Silver, Gold, and Platinum names, NGN prices, durations, badges, and benefits.
2. Activate the one-time 14-day Free package and try it again.
3. Purchase a paid 30-day package and test successful callback.
4. Test cancelled/failed checkout and refresh history.

Expected result: Catalog matches configured values; Free completes without external checkout and cannot be reused; paid checkout uses the exact price; callback status is honest; history shows transaction, state, paid/created dates, and expiry; current package reflects an unexpired completed payment only.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-027 - Join a webcam booking video room

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm students can enter the correct lesson room securely.

Preconditions / test data: Confirmed webcam booking with schedule; Jitsi available.

Steps:

1. Open Video Room from the booking.
2. Before the access window, attempt to open the room link.
3. During the valid window, join and test microphone, camera, chat, screen share, hand raise, tile view, captions, and hang up.
4. Retry after the lesson end.

Expected result: The selected room matches the booking/teacher; early access is denied with schedule details; valid access joins successfully; controls operate or show permission guidance; expired access is denied; another booking's room cannot be inferred or entered.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-028 - Submit feedback, complaint, and issue tickets

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm student support requests are categorized and acknowledged.

Preconditions / test data: Logged-in student.

Steps:

1. Submit Feedback with category, title, and at least ten characters.
2. Submit Complaint with related booking/payment reference.
3. Submit Issues for normal, high, and urgent severity.
4. Try missing category/title, short message, and excessive values.

Expected result: Each valid request produces a unique `PV-` ticket and Open status; kind/category/reference/severity are retained; invalid input stays available for correction; requests are isolated to the user.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-029 - Search and browse FAQ

Priority: Medium  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm self-service help is discoverable.

Preconditions / test data: Logged-in student.

Steps:

1. Search FAQ by question, answer text, and category.
2. Filter each category and expand/collapse results.
3. Enter a no-match query, refresh, and clear filters.

Expected result: Counts and results match query/category; answers expand accessibly; no-match guidance appears; saved search draft belongs only to the current user.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-030 - Secure student account changes with OTP

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm sensitive student settings require a valid, purpose-bound code.

Preconditions / test data: Verified student; alternate unused email/mobile/address; access to inbox.

Steps:

1. Change password, email, mobile, and residential address in separate flows.
2. For each, test unchanged/invalid value, wrong code, expired code, resend, and valid code.
3. Try a code issued for one purpose on another change.
4. Reopen Profile/Verification and log in with updated credentials.

Expected result: Every change requires its own six-character email OTP; unchanged/duplicate/invalid values are rejected; codes are single-use and purpose-bound; valid changes synchronize safely to related student data; old credentials stop working where applicable.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-STU-031 - Permanently delete a student account

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm irreversible deletion is explicit, authenticated, and complete.

Preconditions / test data: Disposable student with profile photo, verification documents, favorites, bookings, messages, and support tickets.

Steps:

1. Start Delete Account and cancel at the warning.
2. Restart, request OTP, and submit wrong then valid code with explicit confirmation.
3. Try to log in and inspect former public/private references.

Expected result: Cancel leaves account intact; deletion requires warning, explicit confirmation, and valid single-use OTP; account/session and owned media are removed; login fails; related data follows defined retention/cascade rules without exposing orphaned personal information.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

## Teacher tests

### PV-TCH-001 - Teacher dashboard and navigation

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the teacher sees the tutor workspace only.

Preconditions / test data: Logged-in teacher.

Steps:

1. Open Dashboard and use Billing, Availability, Bookings, Messages, Verification, Profile, Video Room, Support, Feedback, Issues, Complaint, FAQ, and Settings.
2. Confirm the selected navigation state and direct-link refresh.

Expected result: Teacher pages load and retain identity; student-only Favorites and Student Verification are absent/inaccessible; onboarding status is clear.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-002 - Teacher verification form and draft

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher onboarding data is prefilled and recoverable.

Preconditions / test data: Newly verified teacher account.

Steps:

1. Open Verification.
2. Enter partial biodata, origin, NIN/BVN, qualifications, residence, and notes.
3. Refresh or navigate away and return.
4. Inspect email and name values.

Expected result: Registration name/email are prefilled; email is read-only; partial non-file values restore only for this teacher; verification status is Not Submitted or Incomplete.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-003 - Submit valid teacher identity verification

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a teacher can be verified against NIN and BVN.

Preconditions / test data: Matching biodata, linked mobile, valid 11-digit NIN/BVN, residence, qualification, clear photo, ID document, and qualification document.

Steps:

1. Complete all mandatory identity, origin, qualification, and residence fields.
2. Enter valid NIN and BVN.
3. Upload required photo and both documents.
4. Submit and check confirmation email/status.

Expected result: Identity providers validate matching data; status becomes Approved/Verified; decision date and safe note are saved; verified data synchronizes to account/tutor profile; teacher proceeds to profile completion.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-004 - Reject incomplete or malformed teacher verification

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm all mandatory teacher verification controls are enforced.

Preconditions / test data: Verification form and negative values.

Steps:

1. Submit missing first/last name, mobile, DOB, origin, residence, qualification, NIN, or BVN.
2. Enter malformed mobile, NIN, BVN, date, and mismatched email.
3. Omit each required upload in turn.
4. Select neither/invalid origin dependencies.

Expected result: Submission is blocked with actionable errors; NIN/BVN must each be 11 digits; required photo and documents are enforced; no approval or listing occurs.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-005 - Validate verification file uploads

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher evidence uploads are reliable and safe.

Preconditions / test data: Valid image/PDF plus oversized, unsupported, corrupt, and duplicate-name files.

Steps:

1. Upload a valid profile image, identity image/PDF, and qualification image/PDF.
2. Try each negative file sample.
3. Upload files with the same filename from two accounts.
4. Retry after an interrupted upload.

Expected result: Valid files receive distinct retrievable URLs; unsupported/oversized/corrupt content is rejected without partial submission; filenames do not collide; retry succeeds; private evidence is not exposed through public tutor pages.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-006 - Handle identity mismatch and provider outage

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm verification cannot falsely approve and can recover from provider failure.

Preconditions / test data: Mismatching NIN/BVN/biodata and outage simulation.

Steps:

1. Submit mismatched identity data.
2. Submit during NIN/BVN provider unavailability.
3. Correct data and retry after recovery.

Expected result: Mismatch is rejected; provider outage is reported as temporary, not approved/rejected incorrectly; no duplicate conflicting request is created; corrected data can complete later.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-007 - Approved teacher identity fields are locked

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm approved identity cannot be altered through normal profile requests.

Preconditions / test data: Approved, listed teacher.

Steps:

1. Reopen Verification/Profile.
2. Try to change name, DOB, gender, origin, NIN, BVN, qualification, mobile, address, and evidence directly.
3. Try a stale modified request.

Expected result: Locked fields and files are disabled or denied server-side; address/qualification/mobile changes are routed to OTP Settings and other corrections to Support; no public or verification data diverges.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-008 - Block profile publication before approval and completion

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm only approved and complete teachers become discoverable.

Preconditions / test data: Unverified teacher, approved teacher with incomplete profile.

Steps:

1. Try to save/publish profile before verification approval.
2. After approval, omit display name, headline, bio, subjects, languages, rate, city/state/address, state/LGA of origin in separate attempts.
3. Search public Tutor lists.

Expected result: Pre-approval editing/publication is denied; incomplete save names every missing requirement; teacher remains absent from public search until all required data is saved.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-009 - Complete and publish teacher profile

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm an approved teacher can create the student-facing profile.

Preconditions / test data: Approved teacher; valid profile photo and complete public data.

Steps:

1. Enter headline, positive NGN hourly rate, About, subjects, languages, state/city/address, and allowed profile photo.
2. Select at least one teaching method and save.
3. Refresh Profile and open public Search/Profile as a student.

Expected result: Profile saves once, becomes Listed, and matches the public card/profile; location/photo synchronize; save state changes from unsaved to saved; no verification documents or bank identifiers appear publicly.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-010 - Update allowed public teacher fields

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm allowed profile edits update discovery data.

Preconditions / test data: Approved listed teacher.

Steps:

1. Enter profile edit mode if required.
2. Change headline, About, positive hourly rate, photo, subjects, languages, and teaching methods.
3. Save, refresh, and inspect Search/public profile.
4. Try zero/negative/non-numeric rate.

Expected result: Allowed edits persist and appear publicly; invalid rate is rejected; unsaved-state messaging is accurate; locked identity fields remain unchanged.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-011 - Manage subjects, languages, free first lesson, and methods

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher marketing and delivery options work together.

Preconditions / test data: Approved teacher.

Steps:

1. Add/remove multiple suggested subjects and languages; try duplicates.
2. Toggle Offer first lesson for free.
3. Save Face-to-face only, Webcam only, then both.
4. Try saving with neither method.

Expected result: Lists are normalized without duplicates/empty items; free badge updates on cards; method choices update booking options; at least one method is mandatory; webcam enables Video Room entry.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-012 - Public listing visibility follows teacher state

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm only currently eligible teachers are discoverable.

Preconditions / test data: Not-submitted, rejected, approved-incomplete, approved-listed, frozen, and deleted teachers.

Steps:

1. Search by exact name/subject for each state.
2. Open a previously copied public URL for each ineligible state.

Expected result: Only approved, listed, active, unfrozen teachers appear and load; ineligible URLs return a safe not-found state; unfreezing an approved teacher restores listing according to business rules.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-013 - Create valid future availability

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teachers can publish bookable time slots.

Preconditions / test data: Approved teacher; future start/end values.

Steps:

1. Open Availability and add several future slots.
2. Refresh and compare chronological order.
3. Open public tutor profile as Student.

Expected result: Slots save and return with stable IDs; display is chronological/localized; future slots appear on the public profile; adding a slot does not remove unrelated valid slots.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-014 - Reject invalid and overlapping availability

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm availability remains internally consistent.

Preconditions / test data: Existing future slot.

Steps:

1. Try missing date, malformed date, past start, equal start/end, and end before start.
2. Add a slot partly/fully overlapping the existing slot and a duplicate slot.
3. Attempt more than 50 future slots.

Expected result: Invalid, duplicate, and overlapping slots are rejected without deleting existing availability; the maximum of 50 is enforced; error identifies the conflicting rule. If overlaps are accepted, mark Fail because the PrepVilla requirements require overlap prevention.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-015 - Remove and replace availability

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm availability updates safely.

Preconditions / test data: Several future slots, including one selected by a student in an open page.

Steps:

1. Remove one slot and refresh public profile.
2. Add a replacement slot.
3. From the student's stale page, submit the removed slot.

Expected result: Only the selected slot is removed; public availability updates; replacement appears; stale removed-slot request is rejected and no booking is created.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-016 - View incoming booking requests

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher booking records are complete and role-appropriate.

Preconditions / test data: Slot and range requests using both teaching methods.

Steps:

1. Open Bookings and inspect student name, status, schedule/range, notes, and method.
2. Use each status filter and Refresh.

Expected result: Only this teacher's bookings appear, newest first; all data matches student request; action buttons are correct for each state; no student verification secrets are displayed.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-017 - Accept a requested booking

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher acceptance changes the shared booking state once.

Preconditions / test data: Requested booking owned by teacher; another teacher's booking.

Steps:

1. Click Accept and refresh both teacher/student lists.
2. Try accepting the same booking again.
3. Try accepting another teacher's booking.

Expected result: Own Requested booking becomes Confirmed for both users; duplicate/non-requested acceptance is blocked; foreign booking is denied; Reject buttons disappear appropriately.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-018 - Reject a requested booking

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm rejection closes the request and related conversation.

Preconditions / test data: Requested booking with conversation.

Steps:

1. Click Reject and refresh both accounts.
2. Try to reject again or reject a non-requested/foreign booking.
3. Try to send a message in the related thread.

Expected result: Booking becomes Rejected; conversation becomes blocked; duplicate/non-requested/foreign action is denied; existing messages are not modified.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-019 - Cancel an eligible teacher booking

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the teacher can cancel only own nonterminal bookings.

Preconditions / test data: Own Requested/Confirmed bookings and foreign/terminal bookings.

Steps:

1. Cancel own Requested and Confirmed bookings.
2. Retry and attempt foreign, Completed, Rejected, or Cancelled bookings.

Expected result: Eligible bookings become Cancelled for both roles; terminal/foreign actions are hidden or denied; no payment or unrelated booking is altered incorrectly.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-020 - Teacher completion confirmation and payout gating

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher payout cannot be released before a paid lesson is properly completed.

Preconditions / test data: Future, ended-unpaid, ended-paid Confirmed bookings; student completion states.

Steps:

1. Confirm completion before end and on an unpaid booking.
2. Confirm the ended paid booking as Teacher.
3. Have Student confirm before and after Teacher in separate runs.
4. Try duplicate confirmation and inspect final payout status.

Expected result: Future/unpaid completion is blocked; each role confirms once; payout remains gated until required confirmations/payment; final Completed state is consistent; payout is queued/released once with no duplicate amount.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-021 - Receive and reply to student messages

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teachers can communicate only in their conversations.

Preconditions / test data: Active conversations from two students and another teacher's conversation.

Steps:

1. Open Messages, select each student, and reply.
2. Exchange messages in real time and through fallback reconnect.
3. Try blank message and another teacher's conversation URL.

Expected result: Correct student/thread is shown; messages deliver once in order; blank message is blocked; foreign thread is denied; blocked conversations cannot send.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-022 - Open booking-linked webcam rooms

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm booking rooms are generated only for webcam lessons.

Preconditions / test data: Webcam and face-to-face bookings.

Steps:

1. Open Video Room from the webcam booking.
2. Confirm the room/title/student/schedule and shareable PrepVilla wrapper link.
3. Try to attach/open a video room for face-to-face or foreign booking.

Expected result: Webcam booking maps to one stable PrepVilla room; face-to-face and foreign booking room management is denied; no arbitrary external URL replaces the managed room without validation.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-023 - Create, schedule, copy, and remove teacher video rooms

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm approved teachers can manage standalone lesson rooms.

Preconditions / test data: Approved webcam-enabled teacher; clipboard permission.

Steps:

1. Open the default tutor lobby.
2. Create an instant room.
3. Create a scheduled room with title, future time, duration, and notes.
4. Try a past schedule and invalid duration.
5. Copy/open room link, refresh/sign in again, and remove a saved room.

Expected result: Rooms receive unique `prepvilla-` names and HTTPS wrapper links; future schedule and minimum sensible duration are enforced; saved local rooms restore only for this teacher/browser; copy/open works; removing a standalone room does not alter bookings.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-024 - Use live video-room controls and access window

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm live teaching controls and booking time restrictions behave safely.

Preconditions / test data: Valid booking room; camera/microphone allowed and denied variants.

Steps:

1. Try the booking room before opening and after expiry.
2. Join during the valid window.
3. Test microphone, camera, screen share, chat, whiteboard, captions, reactions, hand raise, participants, tile view, breakout/lobby controls, audio-only, and hang up.
4. Deny browser media permissions and retry.

Expected result: Early/expired rooms are denied clearly; valid room loads; controls are enabled only after join; permission denial gives recovery guidance; hang up disposes the conference; the wrapper never exposes another user's private token.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-025 - Teacher subscription packages and billing history

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher subscriptions use the configured catalog and secure checkout.

Preconditions / test data: New teacher; Flutterwave sandbox outcomes.

Steps:

1. Compare Free, Silver, Gold, and Platinum plans/benefits/prices/durations.
2. Activate Free and try to activate it again later.
3. Purchase a paid package; test success, cancel, fail, delayed callback, and refresh.

Expected result: One-time Free completes for 14 days; paid plans charge exact NGN amount for 30 days; verified callback determines completion; history/current package/expiry are correct; duplicate callback does not duplicate entitlement or ledger entries.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-026 - Contact teacher support

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teachers can request help for locked fields and onboarding.

Preconditions / test data: Logged-in teacher; email service available.

Steps:

1. Open Support and verify name/email/support contacts.
2. Submit subject/message, then submit blank values.
3. Use email and telephone links.
4. Inspect the disabled Chat with Support placeholder.

Expected result: Valid request is emailed with teacher identity and confirms success; blank input is blocked; contact links use correct destinations; unavailable live chat is visibly disabled and does not imply a sent message.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-027 - Submit teacher feedback, complaint, issue, and use FAQ

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm general teacher service channels work.

Preconditions / test data: Logged-in teacher.

Steps:

1. Submit valid Feedback, Complaint with reference, and Issue with severity.
2. Verify ticket numbers and validation for missing/short/excessive data.
3. Search/filter/expand FAQ content for verification, bookings, payouts, subscriptions, video, and support.

Expected result: Each valid request creates a unique Open ticket with correct role/kind/metadata; errors preserve the draft; FAQ search and category counts are accurate.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-028 - Secure teacher password, email, mobile, address, and qualification changes

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm teacher profile corrections use purpose-bound OTP controls.

Preconditions / test data: Approved teacher; alternate values; inbox access.

Steps:

1. Run separate password, email, mobile, residential address, and qualification change flows.
2. Test unchanged/invalid/duplicate values, wrong/expired code, resend, and valid code.
3. Try a code on the wrong purpose.
4. Inspect Profile, Verification, Search, and login after each valid change.

Expected result: Each change requires its own valid single-use code; address/qualification/mobile synchronize to related records; email/password authentication updates; locked-profile rules remain consistent; no partial update occurs on failure.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-029 - Freeze and unfreeze teacher account

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm a teacher can temporarily remove the account from service.

Preconditions / test data: Approved listed teacher; no conflicting active lessons for the test period.

Steps:

1. Try missing, past, reversed, less-than-minimum, and over-three-month date ranges.
2. Enter a valid range, request OTP, submit wrong then correct code.
3. Search for the teacher and attempt teacher actions while frozen.
4. Unfreeze and search again.

Expected result: Date rules are enforced; valid OTP freezes until the selected end and removes listing; frozen status is visible; unfreeze clears it and restores an approved listing; existing records are preserved.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-TCH-030 - Permanently delete teacher account and owned media

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm irreversible teacher deletion removes account access and sensitive assets.

Preconditions / test data: Disposable teacher with photo, verification documents, availability, bookings, conversations, and support records.

Steps:

1. Start deletion and cancel at warning.
2. Request deletion OTP; try invalid then valid code with explicit confirmation.
3. Search/open the former public profile and try login.
4. Verify stored owned media and dependent records follow retention policy.

Expected result: Cancellation is harmless; valid confirmation permanently deletes account and session; public listing disappears; login fails; owned photos/documents are removed; relational data is deleted/anonymized according to policy without privacy leaks.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

## Cross-role and quality tests

### PV-XRL-001 - End-to-end face-to-face lesson journey

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm the primary marketplace journey works across both roles.

Preconditions / test data: Verified student; approved listed face-to-face teacher with availability.

Steps:

1. Student searches, favorites, opens profile, requests a slot, and messages Teacher.
2. Teacher reviews and accepts.
3. Student completes required lesson payment.
4. Both coordinate, lesson ends, and both confirm completion.
5. Student submits review.

Expected result: Every transition appears consistently for both roles; exactly one booking, conversation, payment, completion, payout, and review is recorded; final rating/public profile updates.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-002 - End-to-end webcam lesson journey

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm online lessons work from discovery through completion.

Preconditions / test data: Verified student; approved webcam teacher; future slot; Jitsi available.

Steps:

1. Student requests Webcam and Teacher accepts.
2. Student pays and both open the same booking room.
3. Join during the allowed time and exchange video/chat/screen share.
4. End lesson, confirm completion in both orders, and review.

Expected result: Both roles resolve the same stable room and booking data; time window is enforced; payment/completion/payout/review remain single and consistent.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-003 - Payment integrity and callback idempotency

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm customer charges, platform fee, teacher payable, and payout cannot be duplicated or mismatched.

Preconditions / test data: Subscription and lesson payments; duplicate/out-of-order/tampered callbacks.

Steps:

1. Complete one subscription and one lesson payment.
2. Replay callbacks and webhook events.
3. Send wrong amount/currency/reference/user and invalid signature variants.
4. Complete both booking confirmations and process payout retry.

Expected result: Only valid verified events complete payments; duplicate events are accepted idempotently; mismatches/signature failures do not credit accounts; ledger balances reconcile; teacher and platform transfers occur once and expose safe status to users.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-004 - Timezone and date-boundary consistency

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm schedules remain consistent across user timezones and daylight/date boundaries.

Preconditions / test data: Teacher and student in different timezones; slots near midnight and DST boundary where applicable.

Steps:

1. Teacher creates availability in local time.
2. Student views/requests it in another timezone.
3. Compare API value, both dashboards, video-room window, and completion time.

Expected result: The same instant is stored once and displayed correctly for each user; ordering and date labels remain accurate; no slot moves to an unintended day or opens/expires at the wrong time.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-005 - Responsive layout and browser compatibility

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm key teacher/student journeys work on supported viewports and browsers.

Preconditions / test data: Current Chrome, Safari, Firefox, Edge; desktop, tablet, and mobile widths.

Steps:

1. Repeat login, verification, search, profile, booking, messages, billing, settings, and video-room entry at representative widths.
2. Test browser zoom at 200 percent and portrait/landscape rotation.

Expected result: No clipped fields/actions, horizontal page overflow, unreadable text, hidden validation, or unusable sticky panels; navigation and dialogs remain operable; supported browsers give equivalent outcomes.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-006 - Keyboard and accessibility acceptance

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm core journeys are usable without a mouse and expose meaningful semantics.

Preconditions / test data: Keyboard-only and screen-reader test setup.

Steps:

1. Navigate headings, landmarks, menus, forms, tutor cards, filters, status tabs, FAQ accordions, dialogs, and video controls by keyboard.
2. Trigger errors and success notices.
3. Inspect labels, required state, focus indicator/order, image alternatives, button names, status announcements, and color contrast.

Expected result: All core actions are keyboard reachable; focus is visible/logical and not trapped; controls have accessible names; errors/status are perceivable; content remains understandable without color alone.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-007 - Authorization, privacy, and sensitive-data handling

Priority: Critical  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm users can access only intended data and actions.

Preconditions / test data: Two students, two teachers, logged-out browser, altered IDs/URLs.

Steps:

1. Swap user, tutor, booking, conversation, review, favorite, upload, support, payment, and video-room identifiers.
2. Attempt student actions as teacher and teacher actions as student.
3. Inspect public responses, page source, browser storage, errors, and logs for NIN, BVN, bank details, OTP, tokens, document URLs, and raw provider payloads.

Expected result: Foreign/role-invalid reads and writes are denied consistently; public pages reveal only approved profile data; secrets and full identity/bank data never appear in public output, client logs, URLs, or cross-account drafts.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

### PV-XRL-008 - Failure recovery, duplicate prevention, and acceptable performance

Priority: High  
Status: [ ] Not Run [ ] Pass [ ] Fail [ ] Blocked [ ] Retest Pass  
Tester: ____________ Date: ____________ Environment/build: ____________

Objective: Confirm users can recover from common interruptions without duplicate business records.

Preconditions / test data: Slow/offline network, API 4xx/5xx, refresh/double-click scenarios, representative tutor/message history.

Steps:

1. Interrupt uploads, verification, profile save, availability save, booking, message send, payment return, support submission, and settings OTP.
2. Double-click major submit/payment/action buttons and refresh during processing.
3. Recover network and retry.
4. Observe public search, dashboard, and chat response times with representative data.

Expected result: Loading/disabled states prevent accidental duplicates; failures are readable and retain safe form drafts; retries converge on one record; stale content is not presented as success; key pages become usable within the agreed UAT performance target and chat fallback does not overload the service.

Actual result / evidence: ________________________________________________________________  
Defect ID: ____________________

## UAT defect record template

Use one record per failed case.

| Field | Value |
| --- | --- |
| Defect ID | |
| Related UAT code | |
| Summary | |
| Severity | Critical / High / Medium / Low |
| Environment/build | |
| Account role and test user | |
| Preconditions/test data | |
| Steps to reproduce | |
| Expected result | |
| Actual result | |
| Evidence link | |
| Owner | |
| Fix version | |
| Retest result/date | |

## UAT sign-off

The PrepVilla UAT cycle is accepted when all Critical and High cases pass or have documented business acceptance, no unresolved Critical/High defects remain, payment and identity-verification records reconcile, both face-to-face and webcam end-to-end journeys pass, and authorization/privacy tests pass without exception.

Business Owner: ____________________ Signature: ____________________ Date: ____________

QA Lead: ___________________________ Signature: ____________________ Date: ____________

Product Owner: _____________________ Signature: ____________________ Date: ____________

Teacher Representative: ____________ Signature: ____________________ Date: ____________

Student Representative: ____________ Signature: ____________________ Date: ____________
