#!/bin/bash
# Double-click this file in Finder to launch the strain analysis software.
# (First time only: Finder may warn about an unidentified developer --
# right-click this file and choose "Open" once to approve it.)

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 was not found on this system."
    echo "Install Python 3, or if using conda, make sure it's initialized in your shell profile."
    read -n 1 -s -r -p "Press any key to close this window..."
    exit 1
fi

python3 -m strain_analysis_pkg
status=$?

if [ $status -ne 0 ]; then
    echo ""
    echo "The program exited with an error (see above)."
fi

read -n 1 -s -r -p "Press any key to close this window..."
