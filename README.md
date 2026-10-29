# Project Blackout PVP – Website

Website for the **Project Blackout PVP** DayZ server. Black and violet design, no build step:
plain HTML, CSS and JavaScript. Fonts are self-hosted, so the site makes no requests to Google.

## Pages

| File           | Content                                                                 |
| -------------- | ----------------------------------------------------------------------- |
| `index.html`   | Home: hero, status bar, features, airdrops, key rules, gallery, join steps |
| `server.html`  | Server info: connection, live status, restart countdown, settings, wipes, mods |
| `rules.html`   | Full rulebook with search, table of contents, linkable rules and penalty table |
| `join.html`    | Join guide: DayZ Launcher / DZSA Launcher, first-hour tips, troubleshooting |
| `faq.html`     | Searchable FAQ                                                          |
| `team.html`    | Staff team, staff code and how to apply                                 |
| `support.html` | Reports, ban appeals, bug reports and copyable ticket templates          |
| `404.html`     | “Signal lost” error page (used automatically by GitHub Pages and Netlify) |

```
assets/css/style.css  styles
assets/css/fonts.css  self-hosted fonts
assets/js/config.js   server settings (IP, port, map, Discord, restarts, mods …)
assets/js/main.js     interactions shared by all pages
assets/fonts/         Oswald, Inter, JetBrains Mono (SIL Open Font License)
assets/img/           images and logo
```

## Setup

Edit **`assets/js/config.js`**. The values show up on every page automatically:

| Field             | Purpose                                                                 |
| ----------------- | ----------------------------------------------------------------------- |
| `ip`, `port`      | Server address, shown and copied with one click                         |
| `map`             | Map name                                                                |
| `maxPlayers`      | Slot count                                                              |
| `discord`         | Discord invite link (used by every Discord button)                      |
| `restartTimes`    | Daily restarts in server time, powers the “Next restart” countdown     |
| `timezone`        | The server's time zone, e.g. `Europe/Berlin`                            |
| `mods`            | Required mods, listed on the Join and Server pages (empty = hidden)     |
| `battlemetricsId` | Optional: live online/offline status and player count via BattleMetrics |

Page texts live directly in the HTML files. These parts are **examples** and need to be adapted
to your server – each is marked with an HTML comment:

- `rules.html` – rules, distances, group limit and penalties
- `server.html` – the server settings grid and wipe policy
- `team.html` – staff names, roles and Discord handles
- `faq.html` – answers

The navigation and footer are repeated in every page. If you add or rename a page, update them
in all files.

## Running locally

Open `index.html` in a browser, or start a small web server:

```bash
npx http-server .
# or
python3 -m http.server
```

## Hosting

Any static host works: GitHub Pages, Netlify, Cloudflare Pages or regular web space. Upload
all files as they are. The `3d/` folder is not part of the website and can be left out.

## 3D assets

`3d/planter-box/` holds a Blender model of a wooden planter box for two plants (procedural
generator script, `.blend`, GLB/FBX/OBJ with baked textures). See its
[README](3d/planter-box/README.md).
