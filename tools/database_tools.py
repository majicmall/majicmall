import subprocess


def run(command):
    print(f"\n▶ {command}\n")
    subprocess.run(command, shell=True)


def pause():
    input("\nPress Enter to continue...")


def menu():
    while True:
        print("\n===================================")
        print("    MAJICMALL DATABASE TOOLS")
        print("===================================")
        print("1. Django Check")
        print("2. Show Migration Status")
        print("3. Count Mall Zones")
        print("4. Count Merchant Stores")
        print("5. Count Products")
        print("6. Count Orders")
        print("7. Count Users")
        print("8. Database Summary")
        print("9. Git Status")
        print("10. Return")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            run("python manage.py check")
            pause()

        elif choice == "2":
            run("python manage.py showmigrations")
            pause()

        elif choice == "3":
            run("python manage.py shell -c \"from merchant.models import MallZone; print(f'Mall Zones: {MallZone.objects.count()}')\"")
            pause()

        elif choice == "4":
            run("python manage.py shell -c \"from merchant.models import MerchantStore; print(f'Merchant Stores: {MerchantStore.objects.count()}')\"")
            pause()

        elif choice == "5":
            run("python manage.py shell -c \"from merchant.models import Product; print(f'Products: {Product.objects.count()}')\"")
            pause()

        elif choice == "6":
            run("python manage.py shell -c \"from merchant.models import Order; print(f'Orders: {Order.objects.count()}')\"")
            pause()

        elif choice == "7":
            run("python manage.py shell -c \"from django.contrib.auth import get_user_model; User=get_user_model(); print(f'Users: {User.objects.count()}')\"")
            pause()

        elif choice == "8":
            run("python manage.py shell -c \"from django.contrib.auth import get_user_model; from merchant.models import MallZone, MerchantStore, Product, Order; User=get_user_model(); print('MajicMall Database Summary'); print('--------------------------'); print(f'Users: {User.objects.count()}'); print(f'Mall Zones: {MallZone.objects.count()}'); print(f'Merchant Stores: {MerchantStore.objects.count()}'); print(f'Products: {Product.objects.count()}'); print(f'Orders: {Order.objects.count()}')\"")
            pause()

        elif choice == "9":
            run("git status")
            pause()

        elif choice == "10":
            break

        else:
            print("\nInvalid selection.")


if __name__ == "__main__":
    menu()
