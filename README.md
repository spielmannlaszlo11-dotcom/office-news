# OFFICE / NEWS — GitHub Pages edition

Static website, same premium Guardian dashboard. GitHub Actions retrieves RSS server-side, converts it to JSON, and publishes the website over HTTPS. No laptop or persistent backend required. No third-party CORS proxy.

## Before publishing
GitHub Pages is normally public. Do not upload internal company information or credentials. Guardian's RSS terms allow personal, non-commercial use; confirm that your intended public republication and corporate screen display (including photos) are authorized before deploying. https://www.theguardian.com/help/feeds ; https://licensing.theguardian.com/ . All nine feeds are configured as requested; change `settings.json` to disable any content you are not permitted to publish.

## Deploy (one-time, using a desktop browser or Git)
1. Create a new GitHub repository called `office-news` at https://github.com/new. A public repo on GitHub Free supports Pages and free standard Actions runners. For corporate use check IT policy and appropriate hosting rights first.
2. Extract this ZIP. Upload **the contents**, not the ZIP or enclosing directory. Include the hidden `.github/workflows/news.yml` file, `site/index.html`, `server.py`, `build.py`, `settings.json`, `test_server.py`, `README.md`, and `.gitignore`. If GitHub's upload UI skips hidden files, create `.github/workflows/news.yml` directly using Add file > Create new file and paste the workflow text. The `.nojekyll` file is optional with this artifact workflow.
3. Repository Settings > Pages > Build and deployment > Source > GitHub Actions. No need to select a branch or use a template.
4. Open Actions > Publish OFFICE NEWS > Run workflow > Run workflow (default branch). If Actions are disabled, enable them first. If workflow isn't listed, verify the exact `.github/workflows/news.yml` path on the default branch.
5. Check the build and deploy jobs. The deployment environment shows the real Pages URL. It normally has the form `https://YOUR-USERNAME.github.io/office-news/` (example placeholder, not a deployed URL). Check `health.json` at that address for actual feed counts and errors. If zero stories are available, the screen shows Connecting rather than fabricated news.
6. Open the published URL in iPhone Safari and rotate landscape. Use the same HTTPS URL in Xibo's Webpage widget, with a long widget duration such as 3600 s. The browser polls for updated data every five minutes and changes stories every ten seconds.

## Operations
The cron targets every 5 minutes, offset from the top of the hour. GitHub schedules and Pages/CDN publishing are best-effort; exact 5-minute delivery is not guaranteed. GitHub may disable public-repository schedules after 60 days without repository activity. Run the workflow manually to recover, and monitor it. GitHub Pages is not a guaranteed 24/7 signage SLA. Cache restores the last feed snapshots across runs; GitHub may evict caches. The page labels old or partially failed feeds as cached. The live feed was not reachable from the build environment; check health.json on your first successful deployment. Live Xibo and Safari tests still required. Offline demo: open site/index.html locally on a desktop browser.

For custom settings edit settings.json and run the workflow again. No API keys required for the configured RSS endpoints. Images are fetched by the display from publisher URLs; unavailable images use built-in topic artwork. Some topics may not have recent stories. No live website is created merely by extracting this ZIP.
