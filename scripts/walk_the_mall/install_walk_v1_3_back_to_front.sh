#!/usr/bin/env bash

set -e

cd /workspaces/majicmall
source .venv/bin/activate

TEMPLATE="core/templates/mall/walk_world.html"
VERSION_DIR="backups/walk_the_mall/versions"

mkdir -p "$VERSION_DIR"

if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: $TEMPLATE was not found."
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"

cp "$TEMPLATE" \
  "$VERSION_DIR/walk_before_v1_3_${STAMP}.html"

python <<'PY'
from pathlib import Path
import re
import sys


path = Path("core/templates/mall/walk_world.html")

if not path.exists():
    sys.exit(f"ERROR: Template not found: {path}")

html = path.read_text(encoding="utf-8")

css_start = "/* WALK V1.3 BACK TO FRONT — START */"
css_end = "/* WALK V1.3 BACK TO FRONT — END */"

js_start = "<!-- WALK V1.3 BACK TO FRONT ENGINE — START -->"
js_end = "<!-- WALK V1.3 BACK TO FRONT ENGINE — END -->"

# Safe rerun: remove only this version's previous blocks.
html = re.sub(
    re.escape(css_start) + r".*?" + re.escape(css_end),
    "",
    html,
    flags=re.DOTALL,
)

html = re.sub(
    re.escape(js_start) + r".*?" + re.escape(js_end),
    "",
    html,
    flags=re.DOTALL,
)

queue_css = r'''
    /* WALK V1.3 BACK TO FRONT — START */

    /*
    ============================================================
    CLEANER SCENE

    These architectural pieces are hidden only.
    The current mall background is not modified.
    ============================================================
    */

    .architectural-frame,
    .architecture-column,
    .luxury-marquee,
    .marquee-light-line,
    .storefront-cornice,
    .marble-platform {
      display: none !important;
    }

    /*
    ============================================================
    3D QUEUE STAGE

    The existing merchant design is preserved.

    We are changing only:
    - card position
    - depth
    - scale
    - blur
    - opacity
    - motion
    ============================================================
    */

    .mall-stage {
      perspective: 1500px !important;
      perspective-origin: center 43% !important;
      overflow: visible !important;
    }

    .storefront-shell {
      overflow: visible !important;
      transform-style: preserve-3d !important;
    }

    .storefront-display {
      position: relative !important;
      display: block !important;
      overflow: visible !important;
      transform-style: preserve-3d !important;
    }

    .merchant-storefront {
      position: absolute !important;
      top: 50% !important;
      left: 50% !important;

      width: 100% !important;
      height: 100% !important;

      visibility: visible !important;
      transform-origin: center center !important;
      transform-style: preserve-3d !important;

      transition:
        transform 1450ms cubic-bezier(0.18, 0.82, 0.21, 1),
        opacity 1150ms ease,
        filter 1150ms ease !important;

      will-change:
        transform,
        opacity,
        filter;

      pointer-events: none !important;
    }

    /*
    ============================================================
    FRONT CARD

    Full original size.
    Full original appearance.
    Full interactivity.
    ============================================================
    */

    .merchant-storefront.mm-queue-front {
      z-index: 50 !important;
      opacity: 1 !important;

      filter:
        blur(0)
        brightness(1)
        saturate(1) !important;

      transform:
        translate3d(-50%, -50%, 145px)
        scale(1) !important;

      pointer-events: auto !important;
    }

    /*
    ============================================================
    CARD DIRECTLY BEHIND

    Same card design—only smaller and deeper in the mall.
    ============================================================
    */

    .merchant-storefront.mm-queue-depth-1 {
      z-index: 40 !important;
      opacity: 0.64 !important;

      filter:
        blur(1.15px)
        brightness(0.82)
        saturate(0.9) !important;

      transform:
        translate3d(-50%, -58%, -15px)
        scale(0.79) !important;
    }

    /*
    ============================================================
    THIRD CARD
    ============================================================
    */

    .merchant-storefront.mm-queue-depth-2 {
      z-index: 30 !important;
      opacity: 0.37 !important;

      filter:
        blur(2.65px)
        brightness(0.68)
        saturate(0.78) !important;

      transform:
        translate3d(-50%, -65%, -155px)
        scale(0.61) !important;
    }

    /*
    ============================================================
    DISTANT CARD
    ============================================================
    */

    .merchant-storefront.mm-queue-depth-3 {
      z-index: 20 !important;
      opacity: 0.18 !important;

      filter:
        blur(4.4px)
        brightness(0.54)
        saturate(0.66) !important;

      transform:
        translate3d(-50%, -71%, -275px)
        scale(0.45) !important;
    }

    /*
    Merchants waiting farther down the corridor.
    */

    .merchant-storefront.mm-queue-waiting {
      z-index: 10 !important;
      opacity: 0 !important;

      filter:
        blur(7px)
        brightness(0.44) !important;

      transform:
        translate3d(-50%, -76%, -390px)
        scale(0.32) !important;
    }

    /*
    ============================================================
    EXIT MOTION

    The front merchant continues toward the visitor and exits.
    It never reverses back into the mall.
    ============================================================
    */

    .merchant-storefront.mm-queue-departing {
      z-index: 70 !important;
      opacity: 0 !important;

      filter:
        blur(2.2px)
        brightness(1.08)
        saturate(1.04) !important;

      transform:
        translate3d(-50%, -44%, 470px)
        scale(1.16) !important;

      pointer-events: none !important;
    }

    /*
    Prevent older horizontal slideshow movement from competing
    with the new depth queue.
    */

    .merchant-storefront.is-active,
    .merchant-storefront.is-leaving-left,
    .merchant-storefront.is-entering-left,
    .merchant-storefront.is-leaving-right,
    .merchant-storefront.is-entering-right {
      visibility: visible !important;
    }

    /*
    Keep the existing floor reflection, but center it below
    the approaching merchant.
    */

    .floor-reflection {
      display: block !important;
      opacity: 0.36 !important;
      transform-origin: center center !important;
      animation:
        walkV13FloorPulse
        4.8s
        ease-in-out
        infinite
        alternate !important;
    }

    @keyframes walkV13FloorPulse {
      from {
        opacity: 0.24;
        transform:
          translateX(-50%)
          perspective(500px)
          rotateX(66deg)
          scaleX(0.84);
      }

      to {
        opacity: 0.44;
        transform:
          translateX(-50%)
          perspective(500px)
          rotateX(66deg)
          scaleX(1.05);
      }
    }

    /*
    ============================================================
    MOBILE DEPTH

    Same merchant design. Reduced travel distance only.
    ============================================================
    */

    @media (max-width: 760px) {
      .mall-stage {
        perspective: 1050px !important;
      }

      .merchant-storefront.mm-queue-front {
        transform:
          translate3d(-50%, -50%, 95px)
          scale(1) !important;
      }

      .merchant-storefront.mm-queue-depth-1 {
        opacity: 0.56 !important;

        transform:
          translate3d(-50%, -58%, -10px)
          scale(0.76) !important;
      }

      .merchant-storefront.mm-queue-depth-2 {
        opacity: 0.31 !important;

        transform:
          translate3d(-50%, -65%, -105px)
          scale(0.56) !important;
      }

      .merchant-storefront.mm-queue-depth-3 {
        opacity: 0.14 !important;

        transform:
          translate3d(-50%, -70%, -190px)
          scale(0.4) !important;
      }

      .merchant-storefront.mm-queue-waiting {
        transform:
          translate3d(-50%, -75%, -275px)
          scale(0.28) !important;
      }

      .merchant-storefront.mm-queue-departing {
        transform:
          translate3d(-50%, -43%, 285px)
          scale(1.12) !important;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .merchant-storefront {
        transition-duration: 0.01ms !important;
      }

      .floor-reflection {
        animation: none !important;
      }
    }

    /* WALK V1.3 BACK TO FRONT — END */
'''

style_end = html.rfind("</style>")

if style_end == -1:
    sys.exit("ERROR: Closing </style> tag was not found.")

html = (
    html[:style_end]
    + "\n"
    + queue_css
    + "\n"
    + html[style_end:]
)

queue_js = r'''
  <!-- WALK V1.3 BACK TO FRONT ENGINE — START -->
  <script>
    (() => {
      "use strict";

      const storefronts = Array.from(
        document.querySelectorAll(".merchant-storefront")
      );

      if (!storefronts.length) {
        return;
      }

      const queueClasses = [
        "mm-queue-front",
        "mm-queue-depth-1",
        "mm-queue-depth-2",
        "mm-queue-depth-3",
        "mm-queue-waiting",
        "mm-queue-departing"
      ];

      let previousFront = null;
      let departingCard = null;
      let departureTimer = null;
      let renderFrame = null;

      const activeIndex = () => {
        const index = storefronts.findIndex((card) =>
          card.classList.contains("is-active")
        );

        return index >= 0 ? index : 0;
      };

      const clearQueueClasses = (card) => {
        card.classList.remove(...queueClasses);
      };

      const renderQueue = () => {
        const frontIndex = activeIndex();
        const total = storefronts.length;

        storefronts.forEach((card, index) => {
          if (
            card === departingCard &&
            card.classList.contains("mm-queue-departing")
          ) {
            return;
          }

          clearQueueClasses(card);

          const depth =
            (index - frontIndex + total) % total;

          if (depth === 0) {
            card.classList.add("mm-queue-front");
            card.setAttribute("aria-hidden", "false");
          } else if (depth === 1) {
            card.classList.add("mm-queue-depth-1");
            card.setAttribute("aria-hidden", "true");
          } else if (depth === 2) {
            card.classList.add("mm-queue-depth-2");
            card.setAttribute("aria-hidden", "true");
          } else if (depth === 3) {
            card.classList.add("mm-queue-depth-3");
            card.setAttribute("aria-hidden", "true");
          } else {
            card.classList.add("mm-queue-waiting");
            card.setAttribute("aria-hidden", "true");
          }
        });
      };

      const updateQueue = () => {
        const currentFront =
          storefronts[activeIndex()] || storefronts[0];

        if (
          previousFront &&
          previousFront !== currentFront
        ) {
          window.clearTimeout(departureTimer);

          departingCard = previousFront;
          clearQueueClasses(departingCard);

          departingCard.classList.add(
            "mm-queue-departing"
          );

          departureTimer = window.setTimeout(() => {
            if (departingCard) {
              departingCard.classList.remove(
                "mm-queue-departing"
              );
            }

            departingCard = null;
            renderQueue();
          }, 1350);
        }

        previousFront = currentFront;
        renderQueue();
      };

      const requestQueueUpdate = () => {
        window.cancelAnimationFrame(renderFrame);

        renderFrame = window.requestAnimationFrame(
          updateQueue
        );
      };

      /*
      The existing Walk the Mall controls remain responsible
      for selecting the active merchant.

      This observer only adds the new back-to-front movement.
      */

      const observer = new MutationObserver((mutations) => {
        const changed = mutations.some((mutation) =>
          mutation.type === "attributes" &&
          mutation.attributeName === "class"
        );

        if (changed) {
          requestQueueUpdate();
        }
      });

      storefronts.forEach((card) => {
        observer.observe(card, {
          attributes: true,
          attributeFilter: ["class"]
        });
      });

      renderQueue();

      previousFront =
        storefronts[activeIndex()] || storefronts[0];
    })();
  </script>
  <!-- WALK V1.3 BACK TO FRONT ENGINE — END -->
'''

body_end = html.rfind("</body>")

if body_end == -1:
    sys.exit("ERROR: Closing </body> tag was not found.")

html = (
    html[:body_end]
    + "\n"
    + queue_js
    + "\n"
    + html[body_end:]
)

path.write_text(html, encoding="utf-8")

final = path.read_text(encoding="utf-8")

required = [
    "{% for store in stores %}",
    "merchant-storefront",
    "WALK V1.3 BACK TO FRONT — START",
    "WALK V1.3 BACK TO FRONT ENGINE — START",
    "mm-queue-front",
    "mm-queue-departing",
]

missing = [
    value
    for value in required
    if value not in final
]

if missing:
    sys.exit(
        "ERROR: Installation validation failed:\n- "
        + "\n- ".join(missing)
    )

print()
print("========================================================")
print(" WALK THE MALL V1.3 INSTALLED")
print("========================================================")
print(" Background artwork and background motion: untouched")
print(" Merchant-card visual design: preserved")
print(" Columns and architectural marquee: hidden")
print(" Cards now approach from the back of the mall")
print(" Front card continues forward when leaving")
print(" Existing merchant rotation and controls: preserved")
print("========================================================")
PY

python manage.py check
python manage.py collectstatic --noinput

echo
echo "V1.3 Back-to-Front Queue installed successfully."
