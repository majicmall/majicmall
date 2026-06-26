import subprocess


def run(command):
    print(f"\n▶ {command}\n")
    subprocess.run(command, shell=True)


def pause():
    input("\nPress Enter to continue...")


def menu():
    while True:
        print("\n===================================")
        print("     MAJICMALL PAYMENT TOOLS")
        print("===================================")
        print("1. Verify Stripe Package")
        print("2. Verify PayPal Package")
        print("3. Verify Coinbase Package")
        print("4. Django Check")
        print("5. Git Status")
        print("6. Return")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            run("pip show stripe")
            pause()

        elif choice == "2":
            run("pip show paypalrestsdk")
            pause()

        elif choice == "3":
            run("pip show coinbase-commerce")
            pause()

        elif choice == "4":
            run("python manage.py check")
            pause()

        elif choice == "5":
            run("git status")
            pause()

        elif choice == "6":
            break

        else:
            print("\nInvalid selection.")


if __name__ == "__main__":
    menu()
