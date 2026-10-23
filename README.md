<p align="center"><img src="assets/sleepy.png" width="88" alt="Sleepy"></p>
<h1 align="center">Sleepy</h1>
<p align="center">A quiet desktop companion. Your screen, your models, your keys.</p>

Sleepy is a Python desktop assistant with a floating face, a clean chat window,
on-demand screen context, local chat history, and configurable AI connections.
Windows is the primary tested platform. macOS and Linux desktop builds are
experimental and need real-device testing.

## Download the app

Get the app for your system from [GitHub Releases](https://github.com/veloxite/sleepy/releases).
Choose the Windows installer, Mac app ZIP, or Linux .deb/tarball under **Assets**.
Desktop builds include Python and the UI dependencies. Open Sleepy, go to
**Settings → Models & APIs**, and enter your own provider key. No code edits or
`.env` file are needed. See [installation instructions and platform limits](DISTRIBUTION.md).
Early builds are unsigned previews; macOS/Linux are experimental.

## Run from source (developers)

Install Python 3.12 or newer, download/extract this project, and open a terminal
in its folder. The tested Windows environment uses Python 3.14 and PySide6 6.12.

**Windows**

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe desktop_agent.py --open
```

After setup, run **Create Sleepy Shortcut.ps1** once and double-click
**Sleepy.lnk** whenever you want to open Sleepy. Sleepy supplies its own Windows icon and relaunch command.
Unpin any old Python/Sleepy entry, open the updated app, and pin its running window
once to replace Windows' cached shortcut. The script is only for source users;
installed builds create their own Start menu shortcut.

**macOS (needs testing)**

```sh
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python desktop_agent.py --open
```

Allow screen recording for the app/terminal running Python in macOS System
Settings when you want screen context. Restart Sleepy after changing permission.
Choose online natural voices or native macOS voices in Settings → Voice.
Microphone permission is required for push-to-talk. The Windows shortcut script does not run on a Mac.
Dependencies must offer wheels for
your Python version, OS version, and architecture.

## Bring your own AI

1. Open **Settings → Models & APIs → Add connection**.
2. Pick a provider preset, give it a name, and enter your own API key.
3. **Save connection**, then **Load models** to fetch your provider's model IDs.
4. Choose a **Chat model** and an image-capable **Screen model**. Save again.
5. Choose **Use this connection**. The model name in the chat header opens a
   quick connection/model switcher.

Save as many connections as you need, including multiple Groq accounts or
profiles. Keys are stored using the operating system credential vault, not in
the chat database, source code, or AI messages. Leaving a key blank when editing
keeps the existing key. Changing an endpoint requires a new key to avoid sending
an old provider's credential to another server.

Presets include Groq, OpenAI, OpenRouter, Gemini's compatible API, Ollama on
localhost, a custom OpenAI-compatible Chat Completions endpoint, and native
Anthropic. Anthropic Console keys use Anthropic's Messages API directly,
including system instructions, screen images, tool proposals, usage counters,
rate-limit details, and provider-specific errors. Groq is live-tested; other
providers have automated request-format tests but have not been tested with
live credentials in this source checkout.
Provider access, quotas, model support, and prices vary. There is no automatic
paid fallback or supplied shared API key. Local Ollama needs a separately running
server and an installed model; local image use requires a vision model.

The provider model list can include audio or other non-chat models. Pick models
that support the features you use. For compatible servers, the Compatibility
section controls tool use and the token-limit parameter. A text-only model will
not work with Screen on. Model IDs can also be typed manually.

For Anthropic, choose **Anthropic**, enter a key from Anthropic Console, save,
then load the current Claude model list. Sleepy uses the fixed official API
address and never sends that key to another provider. Anthropic does not accept
OpenAI's `reasoning_effort` parameter, so that setting remains provider-managed.

For Groq, `openai/gpt-oss-120b` is the existing chat default and
`qwen/qwen3.8-27b` is the existing vision default. Use **Load models** for current
availability. Optional `.env` setup is shown in `.env.example`; an existing
GROQ_API_KEY is migrated as a Groq connection without copying the secret into
SQLite. GUI keys take precedence. Removing that connection does not erase a
key that you put in `.env` yourself.

## Everyday use

- Click the companion to chat, drag to move it, or right-click to hide/quit.
  A tray/menu-bar icon brings it back. Close returns to the companion. F11 enters
  full screen, Escape leaves. Launching twice brings forward the existing app.
- Screen on captures once per message. On modern Windows, Sleepy stays visible
  and is excluded only during its own capture; other systems use a brief hide-and-restore
  fallback. Screen off sends text
  and any attached document. The eye button previews the last image sent.
- The **focus-area** button lets you draw around a problem on the primary display.
  Future captures use that area until you remove its chip; select again if you
  move the document. Cancel selection with Escape. Zoom first for tiny symbols.
- Screenshots prefer PNG, then bounded JPEG compression if needed (3.5 MB encoded
  payload and at most 4 million pixels). A provider with tighter limits may still
  reject an image; Sleepy explains the error and asks for a focused screen area.
  Sleepy is instructed to transcribe
  an equation before solving and ask if symbols are unclear. These measures
  reduce avoidable mistakes; they cannot guarantee a model reads every symbol.
- Chats have searchable history, rename and delete controls on the selected row,
  user bubbles, Markdown, LaTeX, highlighted code, and copy buttons.
- Use the speaker beneath a reply to read it aloud. Natural online voices are
  available without an API key; system voices work offline. Code blocks are skipped.
- Appearance settings include light/dark/system themes, built-in backgrounds,
  accent, name, and text size. Companion settings accept images or animated
  GIF/WebP logos. Animations run only near the cursor and reset to their first
  frame when it leaves. Motion can be switched off. Up to 200 frames/25 MB input.
- Memory is an explicit editable note included across chats. Sleepy does not
  silently infer and save personal facts.

## Built-in plugins

**GitHub:** Connect a personal access token in Settings → Plugins. A fine-grained
personal token needs repository Administration: Read and write for repository
creation; account policies can restrict this. The credential goes to GitHub,
never the AI. Ask to create a repository using a model with tool support, or use
the form. Review the name, visibility, and description before confirming. The
plugin creates a repository with a README and defaults to private. It does not
upload this project automatically, edit local files, or execute generated code.

**Document reader:** Attach UTF-8 text/code or a text-based PDF of up to 40 pages
and 25 MB. Up to 24,000 characters are included with each message while attached;
a notice tells you when text is truncated. Scanned PDFs need screen capture.
The file stays attached only in the current chat session; switching chats clears
it. Extracted file text is not saved to history, but the AI's response is.

**Markdown export:** Export the current conversation through Plugins. Code and
math source remain editable. These are built-in abilities, not an open plugin
marketplace. General web-page browsing and arbitrary shell/code execution are
not implemented. Image search, YouTube discovery and explicit desktop actions
are described below.

## Local data and idle behavior

Chats, drafts, preferences, connection metadata, and memories are stored in
`data/agent.sqlite3`. Custom logos are copied into `data/`. The database is
not encrypted; cloud-sync folders may sync it. AI requests include the current
message, up to 16 prior text messages, memories, and any selected screen/document
context. Your selected provider's data policies apply.

Screenshots are kept in memory only; old images are never reattached to later
requests. The preview clears when changing chats or unloading the idle renderer.
There is no continuous screen capture or model polling. API keys live in the
system keyring (Windows Credential Manager or macOS Keychain), except optional
legacy keys explicitly put in `.env`. Do not share the data folder or `.env`.

When far from the pointer, the companion checks proximity once per second and
only repaints when its appearance changes. Hover wakes it immediately. Nearby
animation uses a faster timer while moving, then slows when settled; hiding the
ball stops its animation timer entirely. Custom animated logos stop when away.

Companion-only startup defers loading the chat renderer. After chat is hidden,
the page freezes at about 3 seconds and its renderer is discarded about 20 seconds
later, provided no request, speech, capture or file dialog needs it. Background
updates do not wake a discarded renderer. Music continues through the native
player. Reopening reloads the chat and saved draft; this trades a short reopen
delay for lower idle memory.

New replies preserve existing rendered messages, diagrams and flashcard state.
Closed settings controls are not rebuilt on each reply. The provider SDK loads
on first use; large histories use an indexed, 16-message query for AI context,
without deleting older chats. Unchanged settings are not rewritten to disk.

The Qt host and imported libraries stay resident. Memory can still reach several
hundred MB after chat, voice or music use; longer chats and diagrams add more.
Sleepy does not force working-set trimming or disable GPU acceleration to make
RAM counters look smaller. Battery-life savings have not been measured in watts
or tested across machines. Run `python -m tests.benchmark_idle` on Windows for a
synthetic process-tree CPU/memory check (no API request or microphone capture).

A short Windows measurement on 22 October 2026 used a temporary 80-message chat:

| State | Summed working set | Private committed memory |
| --- | ---: | ---: |
| Companion-only startup, before opening chat | 179 MiB | 92 MiB |
| Hidden after chat renderer was discarded | 260 MiB | 160 MiB |
| Hidden after also loading the provider SDK | 302 MiB | 201 MiB |

These are observed process-tree counters, not memory caps. Working sets can count
shared pages more than once. The 10-second idle samples used 0.3–0.7% of one logical
CPU core; active-window samples varied substantially during startup. This is not
a battery-life test or a guarantee for other machines, long chats, or media use.
Before this update, the hidden renderer waited roughly 63 seconds to unload and
could be reactivated by a background state update; it now unloads after roughly
23 seconds and stays discarded until chat is reopened.


## Development and publishing

See [PUBLISHING.md](PUBLISHING.md) for the safe source-release and GitHub steps.
This project's own code is MIT licensed; dependency notices are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

```sh
python -m unittest discover -v -p "test_*.py"
python -m tests.check_sleepy
python -m tests.check_features
python -m tests.check_study
python -m tests.check_windows
python -m tests.check_assistant
```

The desktop checks open temporary test windows. They use synthetic data and
mocked GitHub calls. `python -m tests.check_sleepy --live` sends a generated full-screen
test card to the configured Groq account; it never sends the user's desktop
unless the test card coverage check succeeds. `python -m tests.check_repo_proposal`
tests an AI proposal without creating a repository. Live checks need a Groq key.

Source layout: `sleepy_app.py` hosts the native shell, `ui/` contains offline chat
rendering, `api_connections.py` manages credentials and profiles, `agent_core.py`
handles compatible chat requests, `focus_overlay.py` selects screen crops,
`github_plugin.py` handles repository creation, and `local_store.py` persists data.
Frontend libraries are vendored with licenses and versions; `fetch_frontend.py`
refreshes them from the official npm registry. API clients and desktop libraries
are installed from `requirements.txt`.

## Study commands

Open **/ Commands** or press **Ctrl+K** (Command+K on Mac). Select a command,
add your question, and send. Screen and attached documents work with all four.

- `/mermaid`: produces a flowchart. The local Mermaid renderer loads when the
  diagram comes into view. Source stays available if a diagram is invalid.
- `/flashcards`: generates a deck in the chat. Click a card to flip it; use Next
  and Previous to review. Cards remain in saved chat history.
- `/eli5`: explains simply and in detail, using everyday examples.

Flowcharts and flashcards also work with natural requests, without slash commands.
Desmos and Excalidraw have been removed; their older source blocks remain readable
in saved history.

A screenshot covers the visible page, not an entire chapter. Attach the chapter
text/PDF for broader coverage. Check generated equations, cards and diagrams.
The external websites have their own privacy policies.

## Connection checks and usage

Settings → Models & APIs has separate tests for the saved chat and screen models.
The screen test sends a generated red square, never your desktop. Tests use your
provider quota. Save changed settings before testing.

Load models also reads capabilities and context/output limits where the provider
exposes them. Known incompatible models are filtered; absent metadata is shown as
**Not reported**, not guessed from a model name. Reply limits are capped by reported
model limits, and reasoning effort is only sent when explicitly supported.

Usage shows a used/remaining chart when the provider reports an allowance. Groq
uses its daily request quota, not money credits. OpenRouter can expose a per-key
spending allowance; account credits require appropriate access. Unknown balances
are never fabricated. Token totals are under Details. Charts are snapshots.
Rate-limit errors offer manual switching; Sleepy never silently changes providers.

The About page currently uses the project description. Add actual repository and
website links after publishing; no placeholder URL is presented as a real project.

## Voice, apps and workspaces

Hold the ball for 0.4 seconds to record, speak, then release. A mouth waveform follows
microphone level. Recording stops on release or after 30 seconds. Chat also has a
hold-to-talk button. Choose a saved Groq/OpenAI speech connection in Settings → Voice;
audio goes there after release and is then discarded. Speech uses provider quota.
Hardware permissions must be enabled on each machine; other speech providers are
not currently wired in.

Natural voice uses edge-tts and sends text to Microsoft's online speech service.
It needs internet but no Windows/Edge installation or API key. Service availability
is not guaranteed; select System voice for offline speech. These options are
implemented for Windows, macOS and Linux, but only Windows is tested here.
iPhone/iPad apps are not included.

Settings → Workspaces lets you add installed apps by name, choose your browser,
and create collections of apps and websites. Say “Open my Physics preset”. File
actions stay in your chosen workspace and show a review before applying. Examples:
“create a folder called Notes”, “rename old.pdf to new.pdf”, or “organize my PDFs”.
PDF organization groups PDFs by modification year, not inferred subject. Existing
destinations are not intentionally overwritten. There is no automatic deletion tool.

On Windows, Sleepy opens beside the active window and restores it when hidden if
it still has the bounds Sleepy set. macOS/Linux use a consistent panel size without
resizing other apps. New launches begin a fresh chat. Empty chats stay out of history.

## Images, video and music

Sleepy can request Wikimedia Commons images when helpful or when asked. Source
links, creator names and available license information accompany the images. Only
short search terms go to the image service. Web thumbnails are saved in chat history;
screen captures are never saved. Thumbnail data is removed from later model context.

Ask for YouTube videos about a topic, or “play [title] on YouTube”. Results open in
your chosen browser. Browser rules may require a click to start playback.

Settings → Music offers SoundCloud public tracks and local audio files, without
client IDs or API forms. SoundCloud mode searches and streams an available public
result. It is not account OAuth or a subscription entitlement; some tracks are
restricted, previews, or unavailable. Such tracks can be opened on the service.
The panel shows the actual title. Hover over the ball while music plays for
previous/pause/next controls. A short click opens chat; holding records. Music
status uses player events, not background polling.

## Linux setup (not yet validated on hardware)

Use the same virtual-environment commands as macOS. A desktop session, Qt platform
libraries, working audio input/output and a Secret Service keyring backend are
required. Screen capture depends on the display server; Wayland may need additional
permissions or tools. Online natural voice is platform independent.

References: [Groq vision](https://console.groq.com/docs/vision),
[Qt speech engines](https://doc.qt.io/qt-6/qttexttospeech-engines.html),
[GitHub Desktop publishing](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop).

## Navigation, music, and workspace layout

The slim left rail opens Workspaces, Music, Plugins, Models & APIs, and Settings.
Settings navigation wraps across the full panel width on narrow windows.
SoundCloud selection saves immediately and remains visibly selected. The global
Save changes button saves voice/appearance preferences without closing Settings.

Hover the companion while music is playing **or paused** to see the music island.
Pause preserves the current track and position; Resume continues. Close stops
playback and dismisses the music controls. The progress bar supports seeking when
the stream does. Broad requests such as “play party music” search for a suitable
mix; specific song/artist requests stay literal. Public search results can vary.
Natural voices are limited to English US and UK; offline voices require a matching
installed system voice.

On Windows, workspace presets open their apps and tile recognized windows on the
monitor where you started the preset. Websites share one browser window when you
select a supported browser. The system-default browser may reuse existing tabs.
Some apps enforce minimum sizes or use window titles Sleepy cannot identify; those
still open, and Sleepy reports that they could not be arranged. Other platforms
open the preset but do not automatically arrange its windows.

## Project folders

- `Sleepy.lnk`: the single everyday Windows launcher (created locally).
- `Create Sleepy Shortcut.ps1`: setup helper to recreate that shortcut.
- Python files in the root: application modules, plus release/setup helpers.
- `ui/` and `assets/`: the interface, bundled libraries, and icons.
- `tests/`: regression tests and developer checks; these do not launch your saved session.
- `data/`, `.env`, and `venv/`: personal data, local configuration, and dependencies; keep these.
- `exports/`: your saved documents, including the older Excalidraw drawing.
- `release/`: clean publication copies, without personal keys or chats.
