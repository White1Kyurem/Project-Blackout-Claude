# Project Blackout PVP – Website

Website for the **Project Blackout PVP** DayZ server. Black and violet design, no build step:
plain HTML, CSS and JavaScript.

## Structure

```
index.html            the page
assets/css/style.css  styles
assets/js/config.js   server settings (IP, port, map, Discord …)
assets/js/main.js     interactions (menu, copy IP, rain & lightning, gallery, live status)
assets/img/           images and logo
```

## Setup

Edit **`assets/js/config.js`**. The values show up everywhere on the page automatically:

| Field             | Purpose                                                                 |
| ----------------- | ----------------------------------------------------------------------- |
| `ip`, `port`      | Server address, shown and copied with one click                         |
| `map`             | Map name                                                                |
| `maxPlayers`      | Slot count                                                              |
| `discord`         | Discord invite link (used by every Discord button)                      |
| `battlemetricsId` | Optional: shows live online/offline status and player count via BattleMetrics |

The section texts (features, rules, join steps) live directly in `index.html`. The rules are
examples; adapt them to your server.

## Running locally

Open `index.html` in a browser, or start a small web server:

```bash
npx http-server .
# or
python3 -m http.server
```

## Hosting

Any static host works: GitHub Pages, Netlify, Cloudflare Pages or regular web space. Upload
all files as they are.
