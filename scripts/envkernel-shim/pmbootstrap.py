#!/bin/sh
# envkernel.sh runs "$pmbootstrap_dir/pmbootstrap.py" directly; route it through
# the project wrapper so the project config, pmaports and work dir are used.
exec "$(dirname "$(readlink -f "$0")")/../pmb" "$@"
