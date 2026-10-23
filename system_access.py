"""Non-invasive desktop diagnostics: never captures or opens the credential vault."""
import os
import shutil
import sys


def report():
    import keyring
    backend = keyring.get_keyring()
    lines = ['Credential storage backend: ' + type(backend).__module__ + '.' + type(backend).__name__,
             'A configured backend may still need to be unlocked before a key can be saved.']
    if sys.platform == 'darwin':
        import Quartz
        import ApplicationServices as AX
        lines += ['Screen Recording: ' + ('allowed' if Quartz.CGPreflightScreenCaptureAccess() else 'permission needed'),
                  'Window arrangement: ' + ('allowed' if AX.AXIsProcessTrusted() else 'Accessibility permission needed'),
                  'Enable these for Sleepy in System Settings → Privacy & Security. Restart after changing Screen Recording.']
    elif sys.platform.startswith('linux'):
        session = os.environ.get('XDG_SESSION_TYPE', 'unknown')
        lines += ['Desktop session: ' + session,
                  'For Wayland capture: PipeWire, xdg-desktop-portal and your desktop’s portal backend must be running. Approve the system sharing picker.',
                  'X11 window arrangement: ' + ('wmctrl found' if shutil.which('wmctrl') else 'install wmctrl'),
                  'Wayland uses desktop-native tiling. Screen permission does not grant window-control access.',
                  'Unlock GNOME Keyring or a compatible Secret Service vault to save API keys.']
    else:
        lines += ['Allow desktop microphone access in Windows Privacy settings for push-to-talk.']
    lines += ['Microphone: allow access when recording is first requested; check the system input device if no speech is detected.',
              'Audio playback: check the output device. Linux requires PipeWire or PulseAudio.',
              'Screen Off does not capture the display. Permission checks here do not send data to an AI provider.']
    return '\n\n'.join(lines)
