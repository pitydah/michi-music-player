# Beta readiness checklist

- [ ] ci_local.sh passes without false positives
- [ ] smoke_ui_routes.py completes without os._exit (errors propagate correctly)
- [ ] GitHub Actions visible and green (packaging + runtime jobs)
- [ ] pytest -q green without unexpected timeout (current: timeout=120s)
- [ ] FileWatcher root-offline safe (does not emit removals for unmounted NAS/USB)
- [ ] Backfill disabled by default (library/auto_backfill_enabled = False)
- [ ] 10k library performance measured (both file-based and db-synthetic)
- [ ] HomeController uses LibraryImportService (no direct w._db.add_file)
- [ ] NavigationController route/sidebar state explicit and tested
- [ ] README state labels honest (no "Estable" without CI evidence)
