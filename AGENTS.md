# Repository Guidelines

## Project Structure & Module Organization
`bed_level_editor.py` drives the Tkinter/Matplotlib GUI for editing the 10x10 mesh from `printer.cfg`. Keep the config file in the repo root; the editor auto-detects it and saves a `.backup` copy before overwriting. Shell helpers live in `run_editor.sh`, dependency pins in `requirements.txt`, and the user-facing overview stays in `README.md`. Store any experimental assets in clearly named subdirectories to avoid polluting the root workspace.

## Build, Test, and Development Commands
Use `pip install -r requirements.txt` to fetch Tkinter-compatible plotting deps (matplotlib, numpy) inside a virtualenv. Launch the GUI with `python3 bed_level_editor.py` for interactive tweaking or `./run_editor.sh` for the guided banner. When validating config parsing without a GUI, run `python3 bed_level_editor.py --help` after adding CLI flags to ensure they load cleanly.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indents and descriptive snake_case identifiers (`mesh_data`, `flatten_mesh`). Keep UI color constants and geometry settings grouped near the top of `BedLevelEditor`. When contributing helper modules, place them beside the main script and guard Tkinter entry points with `if __name__ == "__main__":` to preserve testability.

## Testing Guidelines
There is no automated suite yet; rely on targeted smoke checks. Before opening a PR, load a representative `printer.cfg`, touch several points, run `Level All`, `Offset All Points`, save, and confirm a `.backup` is created. If you add parsing or math helpers, add lightweight doctests or `unittest` cases under a `tests/` folder and name files `test_<feature>.py`.

## Commit & Pull Request Guidelines
Craft commits in the imperative mood (e.g., `Add mesh stats panel`) and keep scope focused. Each PR should describe the change, reference any related printer issues, list manual validation steps (commands run, configs edited), and include screenshots or GIFs for UI adjustments. Highlight any migrations or config format changes so other operators can update their `printer.cfg` safely.

## Configuration & Safety Tips
Never edit `printer.cfg` while Klipper is active; instruct users to stop services first. After saving through the editor, advise restarting firmware and running a verification print. Always leave the auto-generated `printer.cfg.backup` intact until the new mesh is proven on hardware.
