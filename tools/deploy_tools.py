import subprocess
import sys


def run(command, stop_on_error=True):
    print(f"\n▶ {command}")
    result = subprocess.run(command, shell=True)

    if result.returncode != 0 and stop_on_error:
        print(f"\n❌ Command failed: {command}")
        sys.exit(result.returncode)

    return result.returncode


def main():
    print("\n==============================")
    print(" MajicMall Deploy Toolkit")
    print("==============================")

    run("python manage.py check")

    print("\nGit status before deploy:")
    run("git status", stop_on_error=False)

    commit_message = input("\nCommit message: ").strip()

    if not commit_message:
        commit_message = "Update MajicMall Megaverse"

    run("git add -A")
    commit_status = run(f'git commit -m "{commit_message}"', stop_on_error=False)

    if commit_status != 0:
        print("\n⚠️ Nothing to commit or commit failed. Continuing to push just in case.")

    run("git push origin main")

    print("\n✅ Deploy push complete.")
    print("Render should pick up the GitHub push automatically if auto-deploy is enabled.")


if __name__ == "__main__":
    main()