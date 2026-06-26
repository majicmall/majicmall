import subprocess


def run(command):
    print(f"\n▶ {command}\n")
    subprocess.run(command, shell=True)


def pause():
    input("\nPress Enter to continue...")


def menu():

    while True:

        print("\n===================================")
        print("      MAJICMALL MALL TOOLS")
        print("===================================")
        print("1. Verify Intro Pages")
        print("2. Verify Skip Directory Buttons")
        print("3. Django Check")
        print("4. Git Status")
        print("5. Return")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":

            run(
                "find core/templates "
                "-name 'megaverse_home.html' "
                "-o -name 'mall_entrance.html' "
                "-o -name 'grand_reveal.html' "
                "-o -name 'majic_home.html'"
            )

            pause()

        elif choice == "2":

            run(
                'grep -R "skip-directory" core/templates -n'
            )

            pause()

        elif choice == "3":

            run("python manage.py check")

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