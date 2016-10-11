from __future__ import print_function

import sys
import os
import gc
import traceback


def checks():
    failed = False

    # Check Python version
    if sys.version_info < (3, 5):
        print('ERROR: Turbo needs Python 3.5. Python version: {}'.format(sys.version.split()[0]))
        failed = True

    # Check we are not missing folders or files
    dirs = ['config', 'turbo']
    for d in dirs:
        try:
            assert os.path.isdir(d)
        except AssertionError:
            print('ERROR: {} directory not found'.format(d))
            failed = True

    # Termination of the script occurs after all of the checks
    # so that users can see if there is more than one issue
    # rather than run the script, see an issue, fix it, see another
    if failed:
        stop_script()


def stop_script():
    print('\nExiting...')
    sys.exit(1)


def main():
    checks()

    try:
        import turbo
        bot = turbo.Turbo()
        bot.run(bot.config.token)
    except ImportError as e:
        print("ERROR: {}".format(e))
        print("Try running: 'python -m pip install -U -r requirements.txt'")
    except Exception as e:
        if hasattr(e, '__module__') and e.__module__ == 'turbo.exceptions':
            if e.__class__.__name__ == "Shutdown":
                pass
        else:
            traceback.print_exc()
    finally:
        try:
            bot.session.close()  # Close aiohttp session if it is running
        except Exception:
            pass

    gc.collect()  # Garbage collect
    stop_script()


if __name__ == '__main__':
    main()
