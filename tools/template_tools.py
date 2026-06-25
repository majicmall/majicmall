from pathlib import Path


INTRO_FILES = [
    "core/templates/megaverse_home.html",
    "core/templates/mall_entrance.html",
    "core/templates/grand_reveal.html",
    "core/templates/mall/majic_home.html",
]


SKIP_DIRECTORY_CSS = """
.skip-directory {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 22px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 800;
  font-size: .95rem;
  letter-spacing: .03em;
  color: #111;
  background: linear-gradient(135deg,#fff3b0,#d4af37);
  border: 1px solid rgba(255,215,0,.65);
  box-shadow:
      0 0 18px rgba(255,215,0,.35),
      0 8px 25px rgba(0,0,0,.35);
  transition: .25s ease;
}

.skip-directory:hover {
  transform: translateY(-2px) scale(1.03);
  box-shadow:
      0 0 24px rgba(255,215,0,.6),
      0 12px 32px rgba(0,0,0,.45);
}

@media (max-width:768px) {
  .skip-directory {
    top:12px;
    right:12px;
    padding:10px 18px;
    font-size:.85rem;
  }
}
"""


SKIP_DIRECTORY_BUTTON = """
<a href="/directory/" class="skip-directory">
  ⏭ Skip To Directory
</a>
"""


def add_skip_directory_button():
    updated = 0

    for file in INTRO_FILES:
        path = Path(file)

        if not path.exists():
            print(f"SKIPPED missing file: {file}")
            continue

        text = path.read_text(encoding="utf-8")
        changed = False

        if ".skip-directory" not in text:
            text = text.replace("</style>", SKIP_DIRECTORY_CSS + "\n</style>", 1)
            changed = True

        if 'class="skip-directory"' not in text:
            text = text.replace("<body>", "<body>\n" + SKIP_DIRECTORY_BUTTON, 1)
            changed = True

        if changed:
            path.write_text(text, encoding="utf-8")
            updated += 1
            print(f"UPDATED: {file}")
        else:
            print(f"UNCHANGED: {file}")

    print(f"\nDone. Files updated: {updated}")


def verify_skip_directory_button():
    print("\nChecking intro pages...\n")

    for file in INTRO_FILES:
        path = Path(file)

        if not path.exists():
            print(f"❌ Missing: {file}")
            continue

        text = path.read_text(encoding="utf-8")

        has_css = ".skip-directory" in text
        has_button = 'class="skip-directory"' in text

        status = "✅ OK" if has_css and has_button else "⚠️ Needs attention"

        print(f"{status}: {file}")
        print(f"   CSS: {'yes' if has_css else 'no'}")
        print(f"   Button: {'yes' if has_button else 'no'}")


def menu():
    while True:
        print("\n==============================")
        print(" MajicMall Template Toolkit")
        print("==============================")
        print("1. Add Skip To Directory buttons")
        print("2. Verify Skip To Directory buttons")
        print("3. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            add_skip_directory_button()
        elif choice == "2":
            verify_skip_directory_button()
        elif choice == "3":
            print("Exiting toolkit.")
            break
        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    menu()