# SCTechIA Website

Sunshine Coast Tech Alliance website. Static HTML/CSS/JS, no build step.

## Structure
- `index.html` - homepage
- `join.html` - membership tiers / pricing overview
- `join-form.html` - membership registration form (reads `?tier=` from join.html)
- `content/events.json` - upcoming events (editable via `/admin/`)
- `content/board.json` - board members (editable via `/admin/`)
- `admin/` - Decap CMS. Scoped to ONLY events + board members - nothing else on
  the site can be edited through it by design (see `admin/config.yml`).
- `images/` - static assets. `images/uploads/` is where Decap CMS saves any
  new photos uploaded through the admin panel.

## How content updates work
`index.html` fetches `/content/events.json` and `/content/board.json` at page
load and renders the Events and Leadership sections from them (see the
`renderBoard()` / `renderEvents()` functions near the bottom of `index.html`).
Editing those JSON files - either by hand or via `/admin/` - is the only way
to change events or board members. Everything else on the site (pricing,
focus areas, hero copy, footer, nav) is plain static HTML and is NOT wired
to any CMS - it only changes if someone edits the HTML directly and pushes.

## Deploying
This repo is connected to Netlify for continuous deployment - any push to
`main` triggers a new live deploy automatically. There is no manual
`netlify deploy` step needed for normal content changes once `/admin/` is in
use. Headers/redirects/CSP live in `netlify.toml` (git deploys read this
file directly, unlike the old manual `--dir` deploys this site used before).

## Admin access (Decap CMS + Netlify Identity)
- Editors log in at `/admin/` with an email Netlify Identity invite.
- Netlify Identity + Git Gateway must be enabled on the Netlify site for
  this to work (Site settings -> Identity, and Site settings -> Identity ->
  Services -> Git Gateway). This is a one-time setup step.
- To invite someone: Netlify dashboard -> Site -> Identity -> Invite users.
  A save in the admin panel creates a commit on `main` (via Git Gateway),
  which triggers a normal Netlify deploy - same as if a developer pushed it.
