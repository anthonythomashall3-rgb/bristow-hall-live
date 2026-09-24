# Bristow-Hall Rule: the live update

This repository runs the live update of the Bristow-Hall Rule recession indicator, https://bhrrealtime.pages.dev.
Each run fetches the data released that day, rebuilds the indicator, checks what it built, and publishes the site.
Runs start at the release times (a Cloudflare Worker, `worker/`), with GitHub's own schedule as a second line.

- `run_cloud.sh` and `ops/`: the update, its checks, its fallback to the last good version, and its notifications
- `data/105_bristow_hall_system_2026-09-08/`: the rule, its walk-forward record, the site and its templates
- `.github/workflows/`: the update, the monthly rebuild check and the monthly revision drill

Third-party data that may not be republished (index providers, rating agencies, survey and trade publishers) is kept in
a private repository and read at run time; `ops/private_paths.gitignore` lists it. The series are cited on the site's
data page with a link to each publisher.
