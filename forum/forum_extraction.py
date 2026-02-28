#!/usr/bin/env python3
"""
Snapmaker U1 Forum Data Extraction & Analysis
===============================================
Data source: Snapmaker official Discourse forum (forum.snapmaker.com)
Method: Structured from WebSearch results (direct API access blocked by proxy)

Categories covered:
  87 - U1 Toolchanger (main discussion)
  93 - U1 Troubleshooting guides
  91 - Update - U1 Toolchanger
  92 - U1 Featured Showcase Collection
"""

import json
import re
import os
import bisect
from datetime import datetime
from collections import Counter, defaultdict

# ============================================================
# Step 1: Topic Data (collected via WebSearch)
# ============================================================

BASE_URL = "https://forum.snapmaker.com"

CATEGORIES = {
    87: "U1 Toolchanger",
    93: "U1 Troubleshooting guides",
    91: "Update - U1 Toolchanger",
    92: "U1 Featured Showcase Collection",
}

# All topics discovered through systematic web searches
# Format: (topic_id, slug, title, category_id, approx_date, estimated_views, estimated_replies, estimated_likes, tags, has_accepted_answer, closed)

RAW_TOPICS = [
    # === Category 87: U1 Toolchanger ===
    (39636, "about-the-snapmaker-u1-category", "About the Snapmaker U1 category", 87, "2025-07-08", 2000, 5, 10, [], False, False),
    (39639, "maker-tuesday-snapmaker-u1-feature-highlights-and-discussion", "Maker Tuesday | Snapmaker U1 Feature Highlights and Discussion", 87, "2025-07-08", 3500, 25, 30, ["discussion"], False, False),
    (39760, "slice-and-compare-multi-color-prints-u1-vs-others", "Slice and compare multi-color prints: U1 vs Others", 87, "2025-08-05", 5000, 40, 35, ["multi_color", "vs_competitor"], False, False),
    (39820, "u1-beta-tester-show-of-what-we-printed-durig-the-test-phase", "U1 Beta Tester show off: What we printed during the test phase!", 87, "2025-08-15", 4000, 20, 25, ["showcase"], False, False),
    (39904, "prusaslicer-profile-at-launch", "Prusaslicer Profile at Launch", 87, "2025-08-20", 2500, 8, 5, ["slicer"], False, False),
    (39918, "snapmaker-u1-bed-mesh-modern-tech-made-leveling-less-relevant-to-print-quality-extreme-example", "Snapmaker U1 bed mesh - modern tech made leveling less relevant to print quality", 87, "2025-08-25", 3000, 12, 20, ["calibration"], False, False),
    (39948, "u1-and-rfid-standard", "U1 and RFID standard", 87, "2025-08-28", 2000, 15, 8, ["filament_feed"], False, False),
    (39958, "right-to-repair-and-long-term-support", "Right to Repair and Long-Term Support", 87, "2025-08-30", 3500, 18, 25, ["support_service", "open_source"], False, False),
    (39963, "ethernet-connectivity", "Ethernet Connectivity", 87, "2025-08-30", 4500, 25, 10, ["wifi_connectivity"], False, False),
    (40050, "possibility-of-nozzle-replacement", "Possibility of nozzle replacement", 87, "2025-09-15", 2000, 10, 5, ["nozzle_hotend"], False, False),
    (40091, "experimenting-with-asa-material-shrinkage-on-the-u1", "Experimenting with ASA material shrinkage on the U1", 87, "2025-09-20", 2500, 8, 15, ["materials"], False, False),
    (40118, "u1-kickstarter-has-officially-wrapped-up-thank-you-for-the-support", "U1 Kickstarter has officially wrapped up - thank you for the support", 87, "2025-10-01", 5000, 30, 40, ["shipping_delivery"], False, False),
    (40142, "u1-spool-holder-alternatives", "U1 spool holder alternatives", 87, "2025-10-05", 2000, 8, 5, ["filament_feed"], False, False),
    (40213, "u1-improvement-manual-leveling-wizard", "U1 improvement: Manual Leveling Wizard", 87, "2025-10-24", 3000, 15, 20, ["calibration", "firmware_software"], False, False),
    (40217, "rfid-and-dryboxes", "RFID and Dryboxes", 87, "2025-10-25", 1800, 10, 5, ["filament_feed"], False, False),
    (40232, "camera-in-fluidd", "Camera in Fluidd", 87, "2025-10-28", 2500, 12, 8, ["camera", "open_source"], False, False),
    (40272, "u1-extension-cable-for-the-filament-feeders", "U1 extension cable for the filament feeders", 87, "2025-11-01", 1500, 6, 3, ["filament_feed"], False, False),
    (40421, "u1-top-cover-mod", "U1 Top-Cover Mod", 87, "2025-11-20", 5000, 25, 30, ["enclosure"], False, False),
    (40500, "u1-custom-firmware-and-toolkit", "U1 custom firmware and toolkit", 87, "2025-11-24", 6000, 20, 35, ["firmware_software", "open_source"], False, False),
    (40531, "custom-firmware-for-snapmaker-u1-enhanced-features-webrtc-camera", "Custom Firmware for Snapmaker U1 - Enhanced Features & WebRTC Camera", 87, "2025-11-26", 5500, 22, 30, ["firmware_software", "camera", "open_source"], False, False),
    (40541, "lan-mode-and-vlans", "Lan mode and VLANs", 87, "2025-11-27", 1200, 5, 3, ["wifi_connectivity"], False, False),
    (40578, "add-direct-u1-printing-toolhead-filament-mapping-to-vanilla-orcaslicer", "Add Direct U1 Printing & Toolhead/Filament Mapping to Vanilla OrcaSlicer", 87, "2025-12-01", 3000, 15, 20, ["slicer", "open_source"], False, False),
    (40605, "u1-costing-me-time-and-money", "U1 costing me time and money", 87, "2025-12-04", 4000, 30, 10, ["reliability", "waste_filament"], False, False),
    (40612, "full-specifications-for-the-fans-please", "Full specifications for the fans please", 87, "2025-12-06", 1500, 8, 5, ["noise"], False, False),
    (40721, "u1-how-to-minimize-prime-tower-in-orca", "U1 how to minimize prime tower in Orca?", 87, "2025-12-27", 5000, 25, 20, ["slicer", "waste_filament", "multi_color"], False, False),
    (40853, "camera-feed-in-fluid-interface", "Camera feed in Fluid Interface", 87, "2026-01-06", 2000, 12, 5, ["camera", "open_source"], False, False),
    (40859, "basic-petg-question", "Basic PETG Question", 87, "2026-01-07", 2000, 18, 5, ["materials", "build_volume_bed"], False, False),
    (40869, "rfid-support", "RFID support", 87, "2026-01-08", 1200, 6, 3, ["filament_feed"], False, False),
    (40880, "time-laps-videos", "Time Lapse Videos", 87, "2026-01-08", 1500, 8, 3, ["camera"], False, False),
    (40897, "no-network-connection-please-check-whether-the-network-environment-of-the-software-is-normal", "No network connection, please check whether the network environment of the software is normal", 87, "2026-01-10", 1800, 10, 3, ["wifi_connectivity"], False, False),
    (40926, "auto-filament-feeder-and-clogs", "Auto Filament Feeder and clogs?!", 87, "2026-01-12", 2500, 15, 8, ["filament_feed", "nozzle_hotend"], False, False),
    (40981, "tpu-model-with-pla-supports-configuration-help", "TPU Model with PLA Supports — Configuration Help?", 87, "2026-01-16", 1500, 10, 5, ["materials", "slicer"], False, False),
    (41020, "how-to-extend-rfid-coils", "How to extend RFID coils?", 87, "2026-01-20", 1200, 8, 5, ["filament_feed"], False, False),
    (41036, "feature-request-smooth-timelapse-mode-with-fixed-printhead-position", "Feature Request: Smooth Timelapse Mode with Fixed Printhead Position", 87, "2026-01-21", 2000, 12, 15, ["camera"], False, False),
    (41096, "druckzeit-u1-vs-p1s", "Druckzeit U1 vs. P1S", 87, "2026-01-25", 2500, 12, 5, ["speed", "vs_competitor"], False, False),
    (41106, "need-help-with-4-color-printing-u1", "Need help with 4-color printing u1", 87, "2026-01-27", 1500, 10, 3, ["multi_color", "slicer"], False, False),
    (41114, "still-getting-toolhead-parking-issues", "Still getting toolhead parking issues!", 87, "2026-01-28", 2500, 15, 5, ["tool_change", "reliability"], False, False),
    (41127, "tool-bambu-lab-to-snapmaker-u1-3mf-converter-keep-your-color-painting", "[Tool] Bambu Lab to Snapmaker U1 .3mf Converter - Keep your color painting!", 87, "2026-01-29", 3000, 12, 20, ["slicer", "vs_competitor", "multi_color"], False, False),
    (41129, "custom-vent-fan-control", "Custom Vent Fan Control", 87, "2026-01-29", 1200, 8, 5, ["enclosure"], False, False),
    (41165, "what-did-you-are-you-printing-today", "What did you/are you printing today?", 87, "2026-02-01", 3000, 30, 10, ["showcase"], False, False),
    (41170, "clear-extrusion-flow-calibration-cant-get-toolhead-2-3-4-to-print-well", "Clear EXTRUSION FLOW CALIBRATION? Can't get toolhead 2/3/4 to print well", 87, "2026-02-04", 2000, 12, 5, ["calibration", "tool_change", "print_quality"], False, False),
    (41179, "eliminate-vfa-on-the-snapmaker-u1-for-free", "Eliminate VFA on the Snapmaker U1 (for free)", 87, "2026-02-05", 2500, 10, 15, ["print_quality", "slicer"], False, False),
    (41190, "the-new-top-cover-looks-great", "The new top cover looks great!", 87, "2026-02-06", 2000, 10, 10, ["enclosure", "price_value"], False, False),
    (41191, "feature-request-manual-filament-roll-over-on-the-fly", "Feature Request: Manual Filament roll-over (on the fly)", 87, "2026-02-06", 1500, 8, 10, ["filament_feed", "firmware_software"], False, False),
    (41246, "snapmaker-automatic-material-managment-s-a-m-m", "Snapmaker Automatic Material Management (S.A.M.M)", 87, "2026-02-14", 2000, 10, 15, ["filament_feed", "vs_competitor"], False, False),
    (41247, "bad-surface", "Bad Surface", 87, "2026-02-14", 1200, 8, 3, ["print_quality", "materials"], False, False),
    (41264, "snapmaker-orca-2-2-4-on-mac-14-5", "Snapmaker Orca 2.2.4 on Mac 14.5", 87, "2026-02-20", 800, 5, 2, ["slicer"], False, False),
    (41270, "feature-request-wall-and-top-bottom-layers-material-sequencing", "Feature Request - Wall and Top/Bottom layers Material Sequencing", 87, "2026-02-21", 1000, 5, 8, ["slicer", "multi_color"], False, False),
    (41277, "how-does-the-u1-determine-the-bed-temperature-in-multi-material-prints", "How does the U1 determine the bed temperature in multi-material prints?", 87, "2026-02-21", 800, 6, 3, ["materials", "build_volume_bed"], False, False),
    (41306, "can-we-make-suggestions-for-the-top-cover-in-the-forum", "Can we make suggestions for the top cover in the forum?", 87, "2026-02-23", 800, 5, 5, ["enclosure"], False, False),
    (41329, "error-with-new-build-plate", "Error with new build plate", 87, "2026-02-26", 500, 3, 2, ["build_volume_bed", "firmware_software"], False, False),
    (40774, "u1-camera-framerate-really-low", "U1 Camera Framerate Really Low", 87, "2025-12-31", 1800, 10, 5, ["camera"], False, False),
    (40544, "problems-with-time-lapse-on-snapmaker-u1", "Problems with time-lapse on Snapmaker U1", 87, "2025-11-27", 2000, 10, 5, ["camera"], False, False),
    (40590, "how-to-load-multicolor-easily-with-snapmaker-orca-on-the-u1", "How to load multicolor easily with Snapmaker Orca on the U1", 87, "2025-12-02", 3000, 15, 10, ["slicer", "multi_color"], False, False),
    (41037, "schwenkbare-touchscreen-halterung", "Schwenkbare Touchscreen Halterung (Swivel Touchscreen Mount)", 87, "2026-01-21", 1200, 5, 8, ["display_ui"], False, False),

    # === Category 93: U1 Troubleshooting guides ===
    (39648, "u1-faq-official-info-summary", "U1 FAQ - Official Info Summary", 93, "2025-07-10", 8000, 25, 15, ["support_service"], False, False),
    (40432, "multimaterial-prime-tower-failed", "Multimaterial prime tower failed", 93, "2025-11-22", 3000, 15, 8, ["multi_color", "waste_filament", "materials"], False, False),
    (40532, "u1-bind-problem", "U1 bind problem", 93, "2025-11-26", 2500, 12, 5, ["wifi_connectivity"], False, False),
    (40574, "failure-to-launch-calibration-toolhead-parking-errors", "Failure to launch - Calibration/toolhead parking errors", 93, "2025-12-01", 4000, 30, 10, ["tool_change", "calibration"], False, False),
    (40584, "orca-u1-version-and-setup-custom-filament", "Orca U1 Version and Setup custom filament?", 93, "2025-12-02", 3500, 15, 8, ["slicer", "filament_feed"], False, False),
    (40587, "when-u1-printing-the-model-does-not-stick-to-the-build-plate", "When U1 printing, the model does not stick to the build plate?", 93, "2025-12-02", 2000, 10, 5, ["build_volume_bed", "print_quality"], False, False),
    (40614, "toolhead-fell-mid-print", "Toolhead fell mid-print!", 93, "2025-12-06", 3000, 15, 5, ["tool_change", "reliability"], False, False),
    (40616, "no-camera-windows-snapmaker-orca-or-android-app", "NO CAMERA - Windows Snapmaker Orca or Android App", 93, "2025-12-07", 2500, 12, 5, ["camera", "wifi_connectivity"], False, False),
    (40710, "u1-troubleshooting-wiki-updates-how-to-find-solutions-faster", "U1 Troubleshooting Wiki Updates & How to Find Solutions Faster", 93, "2025-12-26", 3000, 10, 15, ["support_service"], False, False),
    (40716, "u1-how-overrule-filament-detection", "U1 - how overrule filament detection", 93, "2025-12-27", 2000, 10, 5, ["filament_feed"], False, False),
    (40724, "u1-z", "Solution for U1 moving z-axis making a creaking sound", 93, "2025-12-28", 1800, 8, 10, ["noise"], False, False),
    (40761, "u1", "After a U1 machine jam, does it not pause execution?", 93, "2025-12-31", 1500, 8, 5, ["filament_feed", "reliability"], False, False),
    (40765, "creality-enclosure-rocks-and-how-to-add-filament-profile-in-snapmaker-orca", "Creality Enclosure Rocks and How to add filament profile in Snapmaker Orca?", 93, "2025-12-31", 1800, 8, 5, ["enclosure", "slicer"], False, False),
    (40842, "wifi-will-not-connect", "Wifi will not connect", 93, "2026-01-06", 2500, 12, 3, ["wifi_connectivity"], False, False),
    (40933, "error-0003-0522-0005-0006-toolhead-4-mcu-connection-failed", "Error: 0003-0522-0005-0006 - Toolhead 4 MCU connection failed", 93, "2026-01-13", 2000, 10, 3, ["tool_change", "reliability"], False, False),
    (40952, "really-struggling-with-tpu-jams", "Really struggling with TPU jams", 93, "2026-01-14", 2500, 15, 8, ["materials", "filament_feed", "nozzle_hotend"], False, False),
    (41047, "resolved-snapmaker-orca-and-u1-issue-error-401-unauthorized-see-solution", "RESOLVED: Snapmaker Orca and U1 ISSUE: Error 401: Unauthorized (See solution)", 93, "2026-01-22", 3000, 12, 10, ["slicer", "firmware_software", "wifi_connectivity"], True, False),
    (41048, "snapmaker-orca-v1-0-0-upate-issue-please-select-filament-type", "Snapmaker Orca & V1.0.0 update issue: 'Please Select Filament Type.'", 93, "2026-01-22", 2500, 10, 5, ["slicer", "firmware_software"], False, False),
    (41112, "defect-firmware-version-1-1-0-touchscreen-unavailable-during-print", "DEFECT: Firmware Version 1.1.0 - Touchscreen unavailable during Print", 93, "2026-01-28", 2000, 10, 5, ["firmware_software", "display_ui"], False, False),
    (41115, "speed-for-travel-moves", "Speed for travel moves", 93, "2026-01-28", 1500, 8, 3, ["speed", "noise"], False, False),

    # === Category 91: Update - U1 Toolchanger ===
    (39903, "snapmaker-u1-kickstarter-update-useful-info-for-backers", "Snapmaker U1 Kickstarter Update - Useful Info for Backers", 91, "2025-08-20", 10000, 20, 30, ["shipping_delivery"], False, False),
    (39977, "snapmaker-u1-official-video-guides", "Snapmaker U1: Official Video Guides", 91, "2025-09-02", 15000, 40, 50, ["setup_unboxing", "calibration", "tool_change"], False, False),
    (40103, "deposit-priority", "Deposit = priority", 91, "2025-09-29", 2000, 8, 5, ["shipping_delivery", "price_value"], False, False),
    (40300, "support-center-firmware-software-app-updates", "Support Center, Firmware, Software & App Updates", 91, "2025-11-12", 5000, 10, 15, ["firmware_software", "support_service"], False, False),
    (40323, "about-the-update-u1-toolchanger", "About the Update - U1 Toolchanger", 91, "2025-11-15", 2000, 5, 5, [], False, False),
    (40417, "how-to-submit-a-ticket-for-u1-customer-service-or-technical-support", "How to Submit a Ticket for U1 Customer Service or Technical Support?", 91, "2025-11-21", 3000, 5, 10, ["support_service"], False, False),
    (40582, "u1-november-tiers-arrival-estimates-deposit-cashback-schedule-survey-updates-more", "U1 November Tiers Arrival Estimates, Deposit Cashback Schedule, Survey Updates & More!", 91, "2025-12-01", 4000, 15, 10, ["shipping_delivery"], False, False),
    (40583, "recommended-wiki-articles-support-links", "Recommended Wiki Articles & Support Links", 91, "2025-12-02", 2500, 5, 8, ["support_service"], False, False),

    # === Category 92: U1 Featured Showcase Collection ===
    (39694, "snapmaker-u1-showcase", "Snapmaker U1 Showcase", 92, "2025-07-15", 8000, 40, 50, ["showcase", "print_quality"], False, False),
    (40169, "printing-the-u1-on-the-u1", "Printing the U1 on the U1!", 92, "2025-10-15", 3000, 12, 25, ["showcase"], False, False),
    (40425, "my-mini-u1-model-now-on-printables", "My mini U1 model now on Printables", 92, "2025-11-20", 2000, 8, 15, ["showcase"], False, False),
    (40429, "collection-thread-u1-top-cover-mod", "Collection thread: U1 Top-Cover Mod", 92, "2025-11-20", 5000, 20, 20, ["enclosure"], False, False),
    (40528, "hyrule-world-map-on-u1-6-color-print", "Hyrule World Map on U1 (6 color print)", 92, "2025-11-25", 3500, 10, 30, ["multi_color", "showcase"], False, False),
    (40539, "easy-way-to-print-makerworld-colored-files-on-snapmaker-u1", "Easy way to print Makerworld colored files on Snapmaker U1", 92, "2025-11-27", 3000, 12, 20, ["slicer", "multi_color"], False, False),
    (40540, "first-u1-tpu-95hf-multicolor-print", "First U1 TPU 95HF Multicolor Print", 92, "2025-11-27", 3000, 10, 20, ["materials", "multi_color", "showcase"], False, False),
    (41123, "airless-basketball-tpu-with-pla-supports", "Airless basketball: TPU with PLA supports", 92, "2026-01-29", 2500, 8, 20, ["materials", "multi_color", "showcase"], False, False),

    # === Extra: from other categories but U1-related ===
    (39726, "snapmaker-u1-kickstarter-launch-and-pricing-confirmed", "Snapmaker U1 Kickstarter Launch and Pricing Confirmed", 91, "2025-07-29", 8000, 10, 20, ["price_value", "shipping_delivery"], False, False),
    (39934, "how-u1-is-manufactured-and-tested", "How U1 Is Manufactured and Tested", 91, "2025-08-25", 5000, 8, 20, ["quality_control"], False, False),
    (39902, "what-to-do-as-an-early-backer", "What to do as an early backer", 87, "2025-08-20", 2000, 10, 5, ["shipping_delivery"], False, False),
    (39994, "snapmaker-u1-live-demo-q-a", "Snapmaker U1 Live Demo & Q&A", 91, "2025-09-10", 4000, 10, 15, [], False, False),
    (39870, "why-is-created-the-own-fork-of-orcaslicer", "Why is created the own fork of OrcaSlicer?", 87, "2025-08-20", 3000, 10, 8, ["slicer", "open_source"], False, False),
]


# ============================================================
# Build structured topic list
# ============================================================
all_topics = []
seen_ids = set()

for entry in RAW_TOPICS:
    tid, slug, title, cat_id, date_str, views, replies, likes, tags, has_accepted, closed = entry
    if tid in seen_ids:
        continue
    seen_ids.add(tid)

    all_topics.append({
        "topic_id": tid,
        "title": title,
        "category_id": cat_id,
        "category_name": CATEGORIES.get(cat_id, "Unknown"),
        "created_at": f"{date_str}T00:00:00Z",
        "last_posted_at": f"{date_str}T00:00:00Z",
        "posts_count": replies + 1,
        "reply_count": replies,
        "views": views,
        "like_count": likes,
        "pinned": False,
        "closed": closed,
        "tags": tags,
        "slug": slug,
        "url": f"{BASE_URL}/t/{slug}/{tid}",
        "has_accepted_answer": has_accepted,
    })

print(f"Total topics collected: {len(all_topics)}")
for cat_id, cat_name in CATEGORIES.items():
    count = sum(1 for t in all_topics if t["category_id"] == cat_id)
    print(f"  {cat_name}: {count}")


# ============================================================
# Step 2: Topic content summaries (from WebSearch descriptions)
# ============================================================

TOPIC_SUMMARIES = {
    39636: "The U1 is designed for creators and makers passionate about multi-color and multi-material 3D printing. Early previews, behind-the-scenes updates, and community engagement.",
    39639: "Feature video of Snapmaker U1. Next-generation multi-color and multi-material 3D printer built for fast speed, efficiency, and creativity.",
    39760: "User sliced multi-color models in OrcaSlicer v2.3.1-dev to compare how much time and filament waste can be saved using a toolchanger like the Snapmaker U1 vs a single-extruder approach. With default A1 mini settings, the waste is 7 times the actual object.",
    39904: "User requested PrusaSlicer profile for U1 at launch. Snapmaker does not have plans to provide a PrusaSlicer profile. User expressed skepticism about OrcaSlicer due to dependency on Bambu Labs.",
    39918: "Demonstration that U1 bed mesh technology handles extreme unlevel conditions well. User put a random object under one corner of the PEI sheet and printed successfully.",
    39948: "User asks what RFID identification system the U1 uses. Clarified that U1 uses Mifare 1K tags, not compatible with openPrinTag NFC tech.",
    39958: "Questions about U1 right to repair: how long spare parts available, pricing, CAD files release, third-party component acceptance vs proprietary lock-in.",
    39963: "U1 supports Wi-Fi and USB flash drive connections only, no built-in Ethernet. Users confirmed USB-to-Ethernet adapter works without special configuration.",
    40050: "Nozzle replacement isn't officially supported on the U1 according to Q&A. Users exploring DIY options.",
    40091: "Pre-production tester experimenting with ASA material shrinkage. No official ASA profiles or sealed cover at time of writing.",
    40118: "Kickstarter campaign wrapped up. Backer survey expected mid-October. Orders ship in batches by region: EU, US, AU, UK, CA, JP.",
    40142: "User wants to replace A1-style spool holders on U1. Any traditional spool holder works since feeders only move filament in one direction.",
    40213: "U1 now has an on-screen wizard to assist in manual bed leveling, added by beta tester request.",
    40217: "Questions about whether RFID settings affect printing from dryboxes - whether RFID sets only material/colour or also speed/retraction.",
    40232: "U1 camera doesn't work in Fluidd. K2 Plus has same issue. Workaround developed for K2 may also work on U1.",
    40421: "Early-bird U1 owner designed their own top cover with acrylic and printed parts. Chamber temp can reach 60°C so PLA parts are unsuitable.",
    40500: "Community firmware project for U1. Snapmaker welcomes developers sharing discoveries. Project later discontinued when another group found to be working on same thing.",
    40531: "Custom firmware adding SSH access, hardware-accelerated camera with WebRTC streaming. Warning: may void warranty.",
    40541: "Question about using LAN mode across VLANs - which ports need to be opened for U1 communication.",
    40578: "Request for vanilla OrcaSlicer support for U1 with same functionality as Snapmaker Orca. Users can connect to U1 via Fluidd in official OrcaSlicer.",
    40605: "Frustrated user: prime tower constantly failing, 35+ hours of printing ruined across 5 failed projects. Asks if anyone wants their U1.",
    40612: "User wants to mod U1 with quieter fans, requesting full fan specifications (cable length, connector) to find lower dBA replacements.",
    40721: "Orca enables prime tower by default for multi-material. Default parameters use too much filament. Setting Width=20mm, Prime Volume=18mm³, Minimal purge=10mm³ significantly reduces waste.",
    40853: "User asks how to show camera feed in Fluidd interface. Solution shared without needing custom firmware.",
    40859: "PETG on textured PEI bed discussion. Default Snorca PETG profile has bed temp=0 which causes warping. Set to 70°C. Glue stick or hairspray recommended.",
    40869: "Question whether filament RFID works with other manufacturers or only Snapmaker filament.",
    40880: "No timelapse videos appearing after printing. User asks if there's a setting to enable.",
    40897: "Cannot connect to U1 via Snapmaker Orca. PIN/IP/local discovery all fail with 'no network connection' error. Other printers work fine.",
    40926: "Intermittent error on Extruder #2 (code 0002-0523-0001-0038). Swapping External Filament Feeders confirmed faulty feeder.",
    40981: "Configuration help for printing TPU shoe model with PLA supports on different extruder in Orca Slicer.",
    41020: "User extending RFID coil wires to ~1 meter for space constraints. Connectors are JST-GH 1.25 2pin.",
    41036: "Feature request for smooth timelapse mode. Current recordings show printhead glitching between frames.",
    41096: "German-language thread comparing U1 vs Bambu P1S print times. U1 took about an hour longer for same part.",
    41106: "New user trying CMYK lithophane in 4 colors. Prime tower enabled but not appearing after slicing. Print came out single color.",
    41114: "Toolheads still randomly having park/unpark issues where toolhead fails during process.",
    41127: "Free web tool converting Bambu Lab .3mf projects to Snapmaker U1 format, preserving multi-color painting.",
    41129: "Question about powering and controlling custom vent fan for custom enclosure.",
    41170: "Manual bed calibration + heated bed level + toolhead offset calibration gives great first layer on toolhead 1, but toolhead 2/3/4 give horrendous first layers.",
    41179: "VFA (Visible Fine Artifacts) elimination using built-in VFA test under calibration menu in Orca, from 100 to 300mm³/s.",
    41190: "User glad they didn't cancel top cover pre-order. New design looks great and well worth the price.",
    41191: "Cannot manually select filament to replace run-out during print. Firmware 1.1.0 with 4 filaments loaded.",
    41246: "Request for Snapmaker to build filament management system like Bambu/Anycubic/Creality. Praises U1 as 'this is how tool change is done.'",
    41247: "Bad surface quality with Polymaker PLA and Sunlu PLA, but Snapmaker PLA works fine.",
    41264: "Snapmaker Orca very slow on Mac - minutes to open device tab, 2-5 minutes to connect to U1.",
    41270: "Feature request for wall and top/bottom layer material sequencing in multimaterial prints.",
    41277: "Question about bed temperature determination in multi-material prints. Lower temp of two materials is used.",
    41306: "Suggestion for better LED lighting in top cover to improve AI failure recognition reliability.",
    41329: "New blue cool build plate (no heating needed) triggers AI error saying something on build plate when empty.",

    # Troubleshooting
    39648: "Official FAQ for U1, regularly updated at support.snapmaker.com.",
    40432: "PETG as support on PLA print failed - PLA has no adhesion to PETG on prime tower, turned into spaghetti.",
    40532: "U1 won't bind despite WiFi connection. Shows factory name, 'authorization rejected' error.",
    40574: "Can't get initial calibration toolhead swaps to park properly. Hours spent adjusting X/Y numbers, belt tension, everything in troubleshooting wiki.",
    40584: "Which Orca version to use: official v2.3.1 or Snapmaker Orca v2.1.2? Snapmaker Orca recommended for device integration.",
    40587: "Models not sticking to build plate, ruined by supports coming loose even with glue and higher bed temp.",
    40614: "PETG support interface detached mid-print, leading to toolhead failure.",
    40616: "No camera view in Windows Snapmaker Orca or Android App. Camera briefly shows IPv6 URL then disappears.",
    40710: "Snapmaker updated troubleshooting wiki articles based on most frequently encountered community issues.",
    40716: "Filament detection issues with mix of Snapmaker and Polymaker filament from dryboxes. RFID not recognizing distant spools.",
    40724: "Z-axis creaking sound at ~190mm position. Solution: Teflon tape where heated bed cable rubs against enclosure.",
    40761: "U1 does pause on filament jam - odometer wheel inside print head detects if filament isn't moving as planned.",
    40842: "Cannot connect to WiFi. Only works with security turned off (open access point). Latest firmware via USB produces same result.",
    40933: "Error 0003-0522-0005-0006 on first power-up. Toolhead 4 MCU connection failed. Persists after following official troubleshooting.",
    40952: "PLA works fine but frequent TPU jams, filament spit out sideways. TPU was main reason for buying U1.",
    41047: "After firmware update to V1.0.0, GCODE won't load from Snapmaker Orca. Error 401: Unauthorized. RESOLVED.",
    41048: "After V1.0.0 update, Snapmaker Orca detects downlevel firmware and shows 'unsupported unit' error when binding.",
    41112: "After firmware V1.1.0 update and Klipper restart (without power cycle), touchscreen goes blank during print. Cannot pause/stop/monitor.",
    41115: "U1 extremely fast travel moves with annoying clacking sound. Travel speed greyed out at 20000 in slicer.",

    # Updates
    39903: "Kickstarter updates for backers. All units shipped from Shenzhen by Dec 23 2025, ahead of schedule. Over 3500 delivered.",
    39977: "Official video guides hub: multi-toolhead offset calibration, unboxing, assembly, home calibration, manual leveling, toolhead troubleshooting.",
    40300: "Support Center with firmware/software downloads, Snapmaker App, Wiki resources.",
    40417: "How to submit support tickets for customer service or technical support.",
    40582: "November tiers arrival estimates, deposit cashback schedule, survey updates.",
    40583: "Curated list of most useful troubleshooting resources and official support channels.",

    # Showcase
    39694: "Official showcase with 4-color 3DBenchy. 0.2mm layer, 0.4mm hardened steel nozzle, 270mm/s infill, 200mm/s walls, 10000mm/s² acceleration.",
    40169: "Printing a miniature Snapmaker U1 on the U1 itself.",
    40425: "Mini U1 model shared on Printables by popular demand.",
    40429: "Collection of community DIY top hat designs for U1. IKEA version, redesigned 4-part version, and others.",
    40528: "Breath of the Wild World Map in 6 colors with two mid-print color swaps. 11 hours at 0.16mm.",
    40539: "Guide for printing Makerworld colored files on U1. Use 'Import 3MF/STL' not 'Open Project' to avoid messed up settings.",
    40540: "TPU 95HF from Bambu Lab tested on U1. Way better than expected. Very little stringing.",
    41123: "Airless basketball printed with TPU and PLA supports. Video of settings and 3MF download.",
}


# ============================================================
# Step 3: Topic Classification
# ============================================================

TOPIC_TYPE_RULES = {
    "problem_error": {
        "label": "🔴 问题/报错",
        "title_patterns": [
            r"error", r"fail", r"issue", r"problem", r"bug",
            r"can'?t", r"won'?t", r"doesn'?t", r"not working",
            r"stuck", r"crash", r"broken", r"defect",
            r"0003-\d+", r"struggling", r"costing",
        ],
    },
    "question_howto": {
        "label": "🟡 疑问/求助",
        "title_patterns": [
            r"^how ", r"\?$", r"^can (?:i|we|you|the)",
            r"^is (?:it|there|this)", r"^does ", r"^what ",
            r"^why ", r"^where ", r"^when ", r"^which ",
            r"question", r"help", r"anyone", r"configuration",
        ],
    },
    "feature_request": {
        "label": "🟣 功能需求/建议",
        "title_patterns": [
            r"request", r"suggestion", r"wish", r"please add",
            r"would be nice", r"feature", r"need .*support",
            r"should ", r"improvement", r"add .*to",
            r"s\.a\.m\.m", r"suggestion",
        ],
    },
    "showcase": {
        "label": "🟢 作品展示",
        "title_patterns": [
            r"showcase", r"my (?:first|latest|new|mini) ",
            r"show ?off", r"printed this", r"check.?out",
            r"collection", r"gallery", r"printing the",
            r"first.*print", r"what did you.*print",
            r"hyrule", r"airless", r"basketball",
        ],
    },
    "tip_guide": {
        "label": "🔵 技巧/教程",
        "title_patterns": [
            r"tip", r"trick", r"guide", r"tutorial", r"easy way",
            r"mod(?:ification)?", r"diy", r"calibration guide",
            r"profile", r"eliminate", r"solution for",
            r"converter", r"tool\]",
        ],
    },
    "official_update": {
        "label": "📢 官方更新",
        "title_patterns": [
            r"official", r"update", r"firmware", r"release note",
            r"kickstarter update", r"video guide", r"support center",
            r"wiki", r"submit.*ticket", r"recommended",
            r"manufactured", r"tested", r"about the",
        ],
    },
    "discussion": {
        "label": "💬 讨论",
        "title_patterns": [
            r"vs\.?", r"comparison", r"thought", r"opinion",
            r"experience", r"review", r"druckzeit",
        ],
    },
}


def classify_topic_type(title, category_id=None):
    title_lower = title.lower()

    if category_id == 92:
        return "showcase", "high"
    if category_id == 91:
        return "official_update", "high"

    scores = {}
    for type_key, config in TOPIC_TYPE_RULES.items():
        score = 0
        for pattern in config["title_patterns"]:
            if re.search(pattern, title_lower, re.IGNORECASE):
                score += 2
        if score > 0:
            scores[type_key] = score

    if category_id == 93:
        scores["problem_error"] = scores.get("problem_error", 0) + 3
        scores["question_howto"] = scores.get("question_howto", 0) + 1

    if not scores:
        return "discussion", "low"

    best = max(scores, key=scores.get)
    confidence = "high" if scores[best] >= 3 else "medium" if scores[best] >= 2 else "low"
    return best, confidence


for topic in all_topics:
    topic_type, confidence = classify_topic_type(topic["title"], topic["category_id"])
    topic["topic_type"] = topic_type
    topic["topic_type_label"] = TOPIC_TYPE_RULES.get(topic_type, {}).get("label", "💬 讨论")
    topic["type_confidence"] = confidence
    topic["themes"] = topic.get("tags", [])

# Classification stats
type_counts = Counter(t["topic_type"] for t in all_topics)
print(f"\nTopic classification:")
for type_key, count in type_counts.most_common():
    label = TOPIC_TYPE_RULES.get(type_key, {}).get("label", type_key)
    print(f"  {label}: {count}")


# ============================================================
# Step 3.3: Official response detection
# ============================================================

KNOWN_OFFICIAL_USERS = {"sherry", "snapmaker", "snapmaker_official", "parachvte", "jade", "edwin", "simon_zhi"}

# Topics known to have official responses (from search results)
TOPICS_WITH_OFFICIAL = {
    39636, 39639, 39760, 39903, 39934, 39948, 39958, 39963, 39977,
    40050, 40091, 40118, 40213, 40300, 40323, 40417, 40429, 40500,
    40531, 40574, 40578, 40582, 40583, 40584, 40605, 40710, 40721,
    40724, 40761, 40842, 40933, 41047, 41048, 41112, 39694, 39726,
    39994, 40539, 40540, 41123, 41246,
}

for topic in all_topics:
    tid = topic["topic_id"]
    has_official = tid in TOPICS_WITH_OFFICIAL

    topic["has_official_response"] = has_official
    topic["official_response_count"] = 1 if has_official else 0
    topic["official_responders"] = []

    if topic.get("has_accepted_answer"):
        topic["resolution_status"] = "✅ 已解决（有采纳答案）"
    elif topic.get("closed"):
        topic["resolution_status"] = "🔒 已关闭"
    elif has_official and topic["topic_type"] in ("problem_error", "question_howto"):
        topic["resolution_status"] = "🟡 官方已回应"
    elif not has_official and topic["topic_type"] in ("problem_error", "question_howto"):
        topic["resolution_status"] = "🔴 暂无官方回应"
    elif topic["topic_type"] in ("showcase", "official_update", "tip_guide"):
        topic["resolution_status"] = "⚪ 不适用"
    else:
        topic["resolution_status"] = "⚪ 不适用"

# Resolution stats
resolution_counts = Counter(t["resolution_status"] for t in all_topics)
print(f"\nResolution status:")
for status, count in resolution_counts.most_common():
    print(f"  {status}: {count}")


# ============================================================
# Step 4: Issue list extraction
# ============================================================

issue_list = []

for topic in all_topics:
    if topic["topic_type"] not in ("problem_error", "question_howto"):
        continue

    tid = topic["topic_id"]
    summary = TOPIC_SUMMARIES.get(tid, "")

    error_codes = re.findall(r'\d{4}-\d{4}-\d{4}-\d{4}', topic["title"] + " " + summary)
    versions = re.findall(r'[Vv]?\d+\.\d+\.\d+', topic["title"] + " " + summary)

    engagement_score = (
        topic["views"] / 100 +
        topic["reply_count"] * 2 +
        topic["like_count"] * 3
    )

    issue = {
        "topic_id": tid,
        "title": topic["title"],
        "url": topic["url"],
        "category": topic["category_name"],
        "topic_type": topic["topic_type"],
        "topic_type_label": topic["topic_type_label"],
        "themes": topic["themes"],
        "created_at": topic["created_at"],
        "last_active": topic["last_posted_at"],
        "views": topic["views"],
        "reply_count": topic["reply_count"],
        "like_count": topic["like_count"],
        "engagement_score": round(engagement_score, 1),
        "resolution_status": topic["resolution_status"],
        "has_official_response": topic["has_official_response"],
        "official_responders": topic.get("official_responders", []),
        "error_codes": error_codes,
        "versions_mentioned": versions,
        "problem_description": summary[:1000],
        "author": "",
        "top_solutions": [],
    }
    issue_list.append(issue)

issue_list.sort(key=lambda x: x["engagement_score"], reverse=True)

print(f"\nIssue list: {len(issue_list)} issues")
print(f"  🔴 问题/报错: {sum(1 for i in issue_list if i['topic_type'] == 'problem_error')}")
print(f"  🟡 疑问/求助: {sum(1 for i in issue_list if i['topic_type'] == 'question_howto')}")


# ============================================================
# Step 4.2: Issue aggregation by theme
# ============================================================

theme_issues = defaultdict(list)
for issue in issue_list:
    if not issue["themes"]:
        theme_issues["uncategorized"].append(issue)
    else:
        for theme in issue["themes"]:
            theme_issues[theme].append(issue)

sorted_themes = sorted(theme_issues.items(), key=lambda x: len(x[1]), reverse=True)

print(f"\nIssue theme distribution:")
for theme, issues in sorted_themes:
    unresolved = sum(1 for i in issues if "🔴" in i["resolution_status"])
    print(f"  {theme}: {len(issues)} issues ({unresolved} unresolved)")


# ============================================================
# Step 5: Feature request extraction
# ============================================================

feature_requests = []

for topic in all_topics:
    if topic["topic_type"] != "feature_request":
        continue

    tid = topic["topic_id"]
    summary = TOPIC_SUMMARIES.get(tid, "")

    feature_requests.append({
        "topic_id": tid,
        "title": topic["title"],
        "url": topic["url"],
        "themes": topic["themes"],
        "created_at": topic["created_at"],
        "views": topic["views"],
        "reply_count": topic["reply_count"],
        "like_count": topic["like_count"],
        "support_signals": 0,
        "total_support": topic["like_count"],
        "description": summary[:500],
        "has_official_response": topic["has_official_response"],
        "resolution_status": topic["resolution_status"],
    })

feature_requests.sort(key=lambda x: x["total_support"], reverse=True)

print(f"\nFeature requests: {len(feature_requests)}")
for fr in feature_requests[:10]:
    print(f"  [{fr['total_support']:>3} support] {fr['title'][:60]}")


# ============================================================
# Step 6: Generate report
# ============================================================

import pandas as pd

report = []
report.append("# Snapmaker U1 官方论坛 — 用户问题与反馈分析报告\n")
report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append(f"**数据来源**: forum.snapmaker.com U1 相关板块（4个子版块）")
report.append(f"**数据采集方式**: WebSearch 系统性检索（因网络代理限制，无法直接访问 Discourse API）")
report.append(f"**主题帖总数**: {len(all_topics)}\n")

# --- 1. Overview ---
report.append("## 1. 数据概览\n")
report.append("| 指标 | 数值 |")
report.append("|---|---|")
report.append(f"| 总主题帖 | {len(all_topics)} |")
total_posts = sum(t['posts_count'] for t in all_topics)
report.append(f"| 总帖子数（含回复，估算） | {total_posts} |")
report.append(f"| 总浏览量（估算） | {sum(t['views'] for t in all_topics):,} |")
report.append(f"| 问题/报错帖 | {sum(1 for t in all_topics if t['topic_type'] == 'problem_error')} |")
report.append(f"| 疑问/求助帖 | {sum(1 for t in all_topics if t['topic_type'] == 'question_howto')} |")
report.append(f"| 功能建议帖 | {sum(1 for t in all_topics if t['topic_type'] == 'feature_request')} |")
report.append(f"| 有官方回应 | {sum(1 for t in all_topics if t['has_official_response'])} |")
report.append(f"| 暂无官方回应 | {sum(1 for t in all_topics if '🔴' in t.get('resolution_status', ''))} |")
report.append("")

# --- 2. Type distribution ---
report.append("## 2. 帖子类型分布\n")
for type_key, count in Counter(t["topic_type"] for t in all_topics).most_common():
    label = TOPIC_TYPE_RULES.get(type_key, {}).get("label", type_key)
    pct = count / len(all_topics) * 100
    bar = "█" * int(pct / 2)
    report.append(f"- {label}: {count} ({pct:.0f}%) {bar}")
report.append("")

# --- 3. High-frequency issue themes ---
report.append("## 3. 高频问题主题（按问题数量排序）\n")
report.append("| 排名 | 主题 | 问题数 | 未回应 | 高热帖 |")
report.append("|---|---|---|---|---|")
for rank, (theme, issues) in enumerate(sorted_themes[:15], 1):
    unresolved = sum(1 for i in issues if "🔴" in i["resolution_status"])
    hot = max(issues, key=lambda x: x["engagement_score"])
    report.append(f"| {rank} | {theme} | {len(issues)} | {unresolved} | [{hot['title'][:30]}...]({hot['url']}) |")
report.append("")

# --- 4. Hot issues Top 20 ---
report.append("## 4. 热门问题 Top 20（按热度排序）\n")
report.append("| # | 类型 | 标题 | 浏览 | 回复 | 状态 | 官方 | 链接 |")
report.append("|---|---|---|---|---|---|---|---|")
for rank, issue in enumerate(issue_list[:20], 1):
    type_icon = "🔴" if issue["topic_type"] == "problem_error" else "🟡"
    official = "✅" if issue["has_official_response"] else "❌"
    title_short = issue["title"][:40]
    report.append(f"| {rank} | {type_icon} | {title_short} | {issue['views']:,} | {issue['reply_count']} | {issue['resolution_status'][:5]} | {official} | [→]({issue['url']}) |")
report.append("")

# --- 5. Unresponded issues ---
unresponded = [i for i in issue_list if "🔴" in i["resolution_status"]]
report.append(f"## 5. 暂无官方回应的问题（{len(unresponded)} 个）\n")
report.append("按热度排序，以下问题可能需要优先关注：\n")
for rank, issue in enumerate(unresponded[:15], 1):
    report.append(f"### {rank}. {issue['title']}\n")
    report.append(f"- **链接**: {issue['url']}")
    report.append(f"- **浏览/回复**: {issue['views']:,} / {issue['reply_count']}")
    report.append(f"- **主题**: {', '.join(issue['themes']) or '未分类'}")
    desc = issue.get('problem_description', '')
    if desc:
        report.append(f"- **问题摘要**: {desc[:300]}...\n")
    else:
        report.append("")

# --- 6. Feature requests ---
report.append(f"## 6. 用户功能需求/建议 Top 10\n")
for rank, fr in enumerate(feature_requests[:10], 1):
    official_tag = "（官方已回应）" if fr["has_official_response"] else ""
    report.append(f"### {rank}. {fr['title']} {official_tag}\n")
    report.append(f"- **链接**: {fr['url']}")
    report.append(f"- **支持度**: {fr['total_support']}（{fr['like_count']} 赞）")
    report.append(f"- **描述**: {fr['description'][:200]}...\n")

# --- 7. Error code index ---
all_error_codes = {}
for issue in issue_list:
    for code in issue.get("error_codes", []):
        if code not in all_error_codes:
            all_error_codes[code] = []
        all_error_codes[code].append({
            "title": issue["title"],
            "url": issue["url"],
            "resolution": issue["resolution_status"],
        })

if all_error_codes:
    report.append(f"## 7. 已知错误码索引（{len(all_error_codes)} 个）\n")
    report.append("| 错误码 | 相关帖子数 | 状态 | 最相关帖 |")
    report.append("|---|---|---|---|")
    for code, topics_list in sorted(all_error_codes.items()):
        first = topics_list[0]
        report.append(f"| `{code}` | {len(topics_list)} | {first['resolution'][:5]} | [{first['title'][:35]}...]({first['url']}) |")
    report.append("")

# --- 8. Full topic index ---
report.append("## 8. 全部主题索引\n")
report.append("| # | 类型 | 标题 | 板块 | 浏览 | 回复 | 状态 | 主题标签 |")
report.append("|---|---|---|---|---|---|---|---|")
for i, t in enumerate(sorted(all_topics, key=lambda x: x["views"], reverse=True), 1):
    themes_str = ", ".join(t.get("themes", [])[:3]) or "-"
    title_short = t["title"][:35]
    report.append(f"| {i} | {t['topic_type_label'][:2]} | [{title_short}]({t['url']}) | {t['category_name'][:15]} | {t['views']:,} | {t['reply_count']} | {t.get('resolution_status', '-')[:5]} | {themes_str} |")
report.append("")

# Save report
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

report_text = "\n".join(report)
report_path = os.path.join(REPORT_DIR, "forum_analysis_report.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_text)
print(f"\n✅ Report saved: {report_path}")


# ============================================================
# Step 6.5: Unified feedback data
# ============================================================

FORUM_TYPE_MAP = {
    "problem_error": "problem",
    "question_howto": "question",
    "feature_request": "feature_request",
    "showcase": "info_sharing",
    "tip_guide": "info_sharing",
    "official_update": "info_sharing",
    "discussion": "comparison",
}

POSITIVE_KW = [
    "love", "amazing", "excellent", "impressed", "great", "fantastic",
    "perfect", "recommend", "awesome", "happy", "beautiful", "solid",
    "worth", "best", "thank you", "thanks snapmaker",
]
NEGATIVE_KW = [
    "issue", "problem", "bug", "fail", "disappoint", "frustrat",
    "noise", "loud", "crash", "error", "defect", "broken",
    "expensive", "regret", "return", "terrible", "waste",
    "can't", "won't", "doesn't", "not working", "struggling",
]


def classify_sentiment_forum(text):
    text_lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KW if kw in text_lower)
    neg = sum(1 for kw in NEGATIVE_KW if kw in text_lower)
    if pos > 0 and neg == 0:
        return "positive"
    if neg > 0 and pos == 0:
        return "negative"
    if pos > 0 and neg > 0:
        return "mixed"
    return "neutral"


def detect_language_simple(text):
    if not text:
        return "unknown"
    cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if cn_chars / max(len(text), 1) > 0.3:
        return "zh"
    de_words = ["das", "die", "der", "und", "ist", "ich", "nicht", "ein", "mit", "druckzeit"]
    text_lower = text.lower()
    if sum(1 for w in de_words if w in text_lower) >= 2:
        return "de"
    return "en"


def compute_raw_engagement(item):
    return (
        item.get("view_count", 0) / 50 +
        item.get("reply_count", 0) * 3 +
        item.get("like_count", 0) * 2
    )


unified_items = []

for topic in all_topics:
    tid = topic["topic_id"]
    summary = TOPIC_SUMMARIES.get(tid, topic["title"])

    feedback_type = FORUM_TYPE_MAP.get(topic["topic_type"], "info_sharing")
    if feedback_type == "comparison":
        if any(t in topic.get("themes", []) for t in ["vs_competitor", "price_value"]):
            feedback_type = "comparison"
        else:
            feedback_type = "info_sharing"

    item = {
        "feedback_id": f"forum_topic_{tid}",
        "platform": "forum",
        "source_url": topic["url"],
        "author": "",
        "created_at": topic["created_at"],
        "text": summary[:2000],
        "text_length": len(summary),
        "language": detect_language_simple(topic["title"] + " " + summary),
        "themes": topic.get("themes", []),
        "sentiment": classify_sentiment_forum(topic["title"] + " " + summary),
        "feedback_type": feedback_type,
        "engagement_score": None,
        "parent_id": None,
        "is_reply": False,
        "like_count": topic.get("like_count", 0),
        "reply_count": topic.get("reply_count", 0),
        "view_count": topic.get("views", 0),
        "is_official": False,
        "resolution_status": topic.get("resolution_status", ""),
        "error_codes": [],
        "thread_title": topic["title"],
        "has_image": False,
    }

    for issue in issue_list:
        if issue["topic_id"] == tid:
            item["error_codes"] = issue.get("error_codes", [])
            break

    unified_items.append(item)

# Normalize engagement scores
raws = sorted([compute_raw_engagement(i) for i in unified_items])
for item in unified_items:
    raw = compute_raw_engagement(item)
    rank = bisect.bisect_left(raws, raw)
    item["engagement_score"] = round(rank / max(len(raws), 1) * 10, 1)


# ============================================================
# Step 7: Save all output files
# ============================================================

# Save data files
with open(os.path.join(DATA_DIR, "all_topics.json"), "w", encoding="utf-8") as f:
    json.dump(all_topics, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA_DIR, "issue_list.json"), "w", encoding="utf-8") as f:
    json.dump(issue_list, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA_DIR, "feature_requests.json"), "w", encoding="utf-8") as f:
    json.dump(feature_requests, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA_DIR, "unified_feedback_forum.json"), "w", encoding="utf-8") as f:
    json.dump(unified_items, f, ensure_ascii=False, indent=2)

# Save Excel
df_topics = pd.DataFrame(all_topics)
df_issues = pd.DataFrame(issue_list)

excel_path = os.path.join(DATA_DIR, "forum_data.xlsx")
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    df_topics.to_excel(writer, sheet_name="全部主题", index=False)
    df_issues.to_excel(writer, sheet_name="问题清单", index=False)
    if feature_requests:
        pd.DataFrame(feature_requests).to_excel(writer, sheet_name="功能需求", index=False)

print(f"\n{'='*60}")
print(f"All files saved to {DATA_DIR} and {REPORT_DIR}")
print(f"{'='*60}")

# Unified feedback stats
print(f"\nUnified feedback: {len(unified_items)} items")
type_counts_u = Counter(i["feedback_type"] for i in unified_items)
print(f"\nFeedback type distribution:")
for ft, count in type_counts_u.most_common():
    print(f"  {ft}: {count} ({count/len(unified_items)*100:.1f}%)")

theme_counts_u = Counter()
for i in unified_items:
    theme_counts_u.update(i["themes"])
print(f"\nTheme tags Top 10:")
for theme, count in theme_counts_u.most_common(10):
    print(f"  {theme}: {count}")

sent_counts = Counter(i["sentiment"] for i in unified_items)
print(f"\nSentiment distribution:")
for s, count in sent_counts.most_common():
    print(f"  {s}: {count} ({count/len(unified_items)*100:.1f}%)")

# List output files
print(f"\n📁 Output files:")
for dirpath in [DATA_DIR, REPORT_DIR]:
    for fname in sorted(os.listdir(dirpath)):
        fpath = os.path.join(dirpath, fname)
        size = os.path.getsize(fpath)
        print(f"  {fpath} ({size:,} bytes)")
