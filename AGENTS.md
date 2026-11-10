# Working on this project

## Goal
Build a lightweight compositor on GPU Screen Recorder (GSR). Prioritize screen recording with good performance and synchronized audio on Linux. Current foundation: PNG/JPG/GIF layers, microphone-reactive avatar, TOML profiles and TUI. The application is Trama; its visual identity is in assets/brand/. Vision/stages: [docs/plan-rust.md](docs/plan-rust.md). Streaming remains out of scope; public distribution targets Flatpak ([docs/flatpak.md](docs/flatpak.md)); the native .deb recipe is development-only.

It must use fewer resources than OBS with an equivalent scene/quality. The previously mentioned 150 MB is an unmeasured aspiration, not a result or validated limit.

Support/validation target: Wayland/COSMIC. Do not expand X11-only modes; leave unrelated upstream GSR code unchanged.

## Design criteria
- Design a foundation that can incorporate images, animations, scenes and other overlays without rewriting composition. Separate composition and behavior where useful; do not build a framework for hypothetical features.
- Prefer simple, readable solutions with few dependencies. Choose languages, interfaces and mechanisms after inspecting GSR rather than fixing architecture from earlier proposals.
- Verify APIs, licenses, versions and compatibility in official sources and actual code. Do not assume a suitable plugin interface exists.
- Reuse GSR for capture/encoding. Justify core changes. Keep personal assets outside the project; use neutral examples/assets samples in tests. Verify GIF timing, loops and transparency.

## Collaboration
- Communicate with the user in Spanish. The AI implements; the user evaluates product and architecture. Briefly explain important decisions and data flow. Project documentation is in English.
- Inspect the project and preserve others' changes. Continue small authorized tasks and corrections without asking after every step.
- Consult on substantial objective changes or hard-to-reverse commitments. Do not commit, publish or install system software without authorization.

## Validation and continuity
- Current continuation checkpoint: [docs/handoff.md](docs/handoff.md). Read it before resuming release work; inspect the real repository state as well.
- Use real checks proportional to the change. Distinguish local checks from pending target-machine validation: Pop!_OS/COSMIC, Intel Iris Xe and 8 GB RAM.
- Measure the process set and CPU, memory, GPU, smoothness and stability against GSR alone and OBS under equivalent conditions. Claim no advantages without measurements.
- First achieve a small end-to-end flow, then expand. If resource advantage is not met, resolve that before adding features.
- Keep this file brief. Record continuation state and decisions in separate documentation when needed; reference only existing files.
- Deliver results, validation, limitations and next step. Do not invent test results or compatibility.
