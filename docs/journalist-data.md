# Journalist Contact Data Policy

OpenClaw separates **coverage discovery** from **contact verification**. An
article byline proves that a person covered a subject; it does not prove any
guessed email address.

## Accepted ways to obtain an email

1. A public author/profile page on the journalist's publication.
2. An outlet masthead, newsroom directory, or contact page.
3. A professional profile where the journalist explicitly publishes a work
   email for pitches.
4. A licensed media database such as Muck Rack or Cision, subject to its terms
   and your subscription rights.
5. A reputable verification provider used to check an address you already
   have a lawful reason to contact. Verification is not permission to scrape,
   resell, or spam the address.

## Required record fields

- `email`: the address exactly as published or provided.
- `email_status`: `public`, `verified`, `unverified`, `missing`, or `invalid`.
- `email_source_url`: public source URL when one exists.
- `email_source_note`: provider name/reference or other evidence.
- `email_verified_at` and `email_last_checked_at`: timestamps for later review.

Only `public` and `verified` contacts can be selected for real outreach in the
dashboard. Re-check contacts periodically because journalists change outlets
and roles frequently.

## Prohibited shortcuts

- Do not create `firstname.lastname@outlet.com` and label it real.
- Do not treat a valid domain or MX record as proof that a mailbox exists.
- Do not import scraped/purchased lists without checking provider terms,
  lawful basis, source evidence, and opt-out requirements.
- Do not send to the synthetic `example.com` records used by local tests.

## Recommended operating flow

1. Discover relevant recent coverage in OpenClaw.
2. Confirm the author and current outlet on the original article/profile.
3. Find an explicitly published address or licensed provider record.
4. Record the evidence when adding the journalist.
5. Review the generated pitch manually.
6. Send from a connected Gmail account and honor replies, bounces, and opt-outs.
