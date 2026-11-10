# Ecosystem QML

QML for the Ecosystem dashboard and the Stream Factory wizard lands here from
phase E1 onward (structure per master plan §124).

Rules:

- No transport controls, no mini-player: enforced by
  `tests/architecture/test_repo_boundaries.py`.
- During incubation the development harness may resolve the Player design
  system from the Player checkout; there is never a copied/divergent design
  system (master plan §144 note, P1-REPO-13).
