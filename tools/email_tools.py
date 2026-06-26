import subprocess


def run(command):
    print(f"\n▶ {command}\n")
    subprocess.run(command, shell=True)


def pause():
    input("\nPress Enter to continue...")


def menu():
    while True:
        print("\n===================================")
        print("      MAJICMALL EMAIL TOOLS")
        print("===================================")
        print("1. Django Check")
        print("2. Show Email Settings")
        print("3. Search Email Code")
        print("4. Git Status")
        print("5. Return")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            run("python manage.py check")
            pause()

        elif choice == "2":
            run('python manage.py shell -c "from django.conf import settings; print(\'EMAIL_BACKEND:\', getattr(settings, \'EMAIL_BACKEND\', None)); print(\'DEFAULT_FROM_EMAIL:\', getattr(settings, \'DEFAULT_FROM_EMAIL\', None)); print(\'EMAIL_HOST:\', getattr(settings, \'EMAIL_HOST\', None)); print(\'EMAIL_PORT:\', getattr(settings, \'EMAIL_PORT\', None))"')
            pause()

        elif choice == "3":
            run('grep -R "send_mail\\|EmailMessage\\|EmailMultiAlternatives" . --include="*.py" --exclude-dir=.venv')
            pause()

        elif choice == "4":
            run("git status")
            pause()

        elif choice == "5":
            break

        else:
            print("\nInvalid selection.")


if __name__ == "__main__":
    menu()
