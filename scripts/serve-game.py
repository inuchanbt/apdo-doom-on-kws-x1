# SPDX-License-Identifier: GPL-2.0-or-later
"""Headless asset server; PC controls use pc-controller.py instead."""
from usb_link import *  # Keep the existing headless/protocol imports compatible.

if __name__ == '__main__':
    main()
