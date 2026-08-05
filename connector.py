"""FlowSense edge connector entry point.

Thin wrapper around the flowsense.runner package. Run:
    python connector.py --camera "Simpang DPRD Arah Kota"
"""
import sys

from flowsense.runner import main

if __name__ == "__main__":
    print("\n" + "*"*60)
    print("🌟 FLOWSENSE AI ACTIVATED 🌟")
    print("Welcome back, YOLOv11! You're now live on the edge.")
    print("The city's arteries are flowing, and you are the all-seeing eye.")
    print("Keep those false positives low, keep that inference speed high!")
    print("Every detection counts. Every bounding box matters.")
    print("Let's bring order to the chaos of traffic. You got this!!")
    print("*"*60 + "\n")
    sys.exit(main())
