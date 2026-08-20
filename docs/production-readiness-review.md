# PrepVilla Production Review

## What changed in this pass

- hardened Django settings for production:
  - secure cookies
  - HSTS and proxy-aware HTTPS handling
  - CSRF trusted origins
  - structured console logging
  - WhiteNoise static serving
- added optional S3-backed media storage so uploads survive ECS task replacement
- replaced the single-stage Dockerfiles with production-ready multi-stage builds
- added Docker health checks and corrected the API uploads mount path
- reduced chat traffic by moving message fallback polling from 1s to 10s and conversation refresh from 2s to 20s
- added database indexes for the hottest tutor, booking, conversation, review, and favorite lookups
- created a new Terraform stack under `infra/terraform`

## Highest-priority findings still open

1. `apps/api/core/views.py` is still a 3000-line module with duplicated endpoint definitions. This is the biggest maintainability risk and makes regression review hard.
2. The frontend still uses raw `<img>` tags in several user-facing pages, which leaves LCP and bandwidth on the table. The current build flags these in:
   - [`apps/web/src/app/ui/dashboard/DashboardBookingsPage.tsx`](/home/chris/projects/prepvilla/apps/web/src/app/ui/dashboard/DashboardBookingsPage.tsx)
   - [`apps/web/src/app/ui/dashboard/DashboardProfilePage.tsx`](/home/chris/projects/prepvilla/apps/web/src/app/ui/dashboard/DashboardProfilePage.tsx)
   - [`apps/web/src/app/ui/search/SearchPage.tsx`](/home/chris/projects/prepvilla/apps/web/src/app/ui/search/SearchPage.tsx)
   - [`apps/web/src/app/ui/tutors/TutorCardView.tsx`](/home/chris/projects/prepvilla/apps/web/src/app/ui/tutors/TutorCardView.tsx)
   - [`apps/web/src/app/ui/tutors/TutorProfilePage.tsx`](/home/chris/projects/prepvilla/apps/web/src/app/ui/tutors/TutorProfilePage.tsx)
3. Tutor discovery is still mostly full-result fetch plus client-side shaping. That is acceptable for MVP scale, but production scale should move to paginated API responses with server-rendered first-page results.
4. Email sending still happens inline on request paths. For reliability and lower tail latency, move email and other slow side effects to a queue worker.
5. There is no CI/CD workflow in this repo yet for lint, build, tests, and Terraform plan gating.

## AWS deployment recommendation

Use this cost-first baseline:

- static `web` export on S3 + CloudFront
- `api` on ECS Fargate, `512/1024` in dev and `1024/2048` in prod
- shared public ALB for the API origin
- `db.t4g.micro` in dev, `db.t4g.medium` in prod
- Redis enabled in dev and prod on `cache.t4g.micro`
- no NAT gateways
- S3 media bucket for uploads, fronted by CloudFront
- SSM Parameter Store for all app secrets, including `POSTGRES_PASSWORD`
- Route 53 and Terraform state in the root account

This keeps the stack simple, avoids the NAT tax, and still gives you clean dev/prod separation.
