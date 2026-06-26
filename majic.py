import subprocess
import sys


def run(command):
    subprocess.run(command, shell=True)


def pause():
    input("\nPress Enter to continue...")


def coming_soon(name):
    print(f"\n{name} is coming soon.")
    pause()


def main():

    while True:

        print("\n=========================================")
        print("   MAJICMALL MEGAVERSE DEVELOPER HUB")
        print("=========================================")
        print("1. 🚀 Deploy Project")
        print("2. 🧩 Template Tools")
        print("3. 🏬 Mall Tools")
        print("4. 🏪 Merchant Tools")
        print("5. 🎬 Theater Tools")
        print("6. 💳 Payment Tools")
        print("7. 📧 Email Tools")
        print("8. 🗄 Database Tools")
        print("9. 🖼 Image Tools")
        print("10. 🩺 Diagnostics")
        print("11. 🤖 AI Team Tools")
        print("12. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":

            run("python tools/deploy_tools.py")

        elif choice == "2":

            run("python tools/template_tools.py")

        elif choice == "3":

            run("python tools/mall_tools.py")

        elif choice == "4":

            run("python tools/merchant_tools.py")

        elif choice == "5":

            coming_soon("Theater Tools")

        elif choice == "6":
            run("python tools/payment_tools.py")

        elif choice  == "7":

            coming_soon("Email Tools")

        elif choice == "8":

            coming_soon("Database Tools")

        elif choice == "9":

            coming_soon("Image Tools")

        elif choice == "10":

            coming_soon("Diagnostics")

        elif choice == "11":

            coming_soon("AI Team Tools")

        elif choice == "12":

            print("\nMajicMall Megaverse Developer Hub closed.")
            sys.exit()

        else:

            print("\nInvalid option.")


if __name__ == "__main__":
    main()