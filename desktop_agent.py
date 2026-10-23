"""Sleepy source and packaged application entry point."""
import sys

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        from package_smoke import main
    else:
        from sleepy_app import main
        # Desktop launchers open the app; --ball keeps the quiet startup option.
        if getattr(sys, 'frozen', False) and '--ball' not in sys.argv:
            sys.argv.append('--open')
    raise SystemExit(main())
