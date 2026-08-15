#!/bin/sh
# Open the model in Blender with materials visible (rendered shading).
# Usage: ./view.sh
set -e
dir=$(cd "$(dirname "$0")" && pwd)
exec blender "$dir/out/highrise_house.blend" --python "$dir/open_in_blender.py"
