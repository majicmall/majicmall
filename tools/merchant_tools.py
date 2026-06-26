import subprocess


def run(command):
    print(f"\n▶ {command}\n")
    subprocess.run(command, shell=True)


def pause():
    input("\nPress Enter to continue...")


def menu():

    while True:

        print("\n===================================")
        print("     MAJICMALL MERCHANT TOOLS")
        print("===================================")
        print("1. Verify Merchant Stores")
        print("2. Verify Products")
        print("3. Verify Orders")
        print("4. Django Check")
        print("5. Git Status")
        print("6. Return")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":

            run("python manage.py shell -c \"from merchant.models import MerchantStore; print(f'Merchant Stores: {MerchantStore.objects.count()}')\"")

            pause()

        elif choice == "2":

            run("python manage.py shell -c \"from merchant.models import Product; print(f'Products: {Product.objects.count()}')\"")

            pause()

        elif choice == "3":

            run("python manage.py shell -c \"from merchant.models import Order; print(f'Orders: {Order.objects.count()}')\"")

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