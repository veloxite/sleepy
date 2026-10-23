Sleepy 0.1.0 — first Windows release

**Your desktop. Your data. Your control.** Sleepy is built with privacy in mind, giving you control over your AI providers, API keys, and personal information. Its open-source code lets anyone inspect how the assistant works and handles data.

For Windows 10/11, x64:
- Download `Sleepy-0.1.0-windows-x64-setup.exe` for the installer.
- Or extract the entire portable ZIP and run `Sleepy.exe`, keeping its bundled files together.
- Open Settings → Models & APIs, choose a provider, and enter your own API key. No Python installation or .env file is needed.

macOS and Linux support is in development; downloads will be available soon after further testing.

This release has been tested on a Windows laptop. Automated unit and packaged startup/UI checks also pass. It is unsigned, so Windows may show a SmartScreen reputation warning. Please report issues with reproduction steps, without including API keys or personal screenshots.

Keys use the operating system credential vault. Prompts and selected screen/document context go to your chosen provider. Chats are stored locally without database encryption. Online speech sends reply text to Microsoft's speech service; music and image search use external services. Provider charges and policies apply. No shared API key is included.

See DISTRIBUTION.md for installation, user data, updates, and licenses.
