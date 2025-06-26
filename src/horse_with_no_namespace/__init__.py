# SPDX-FileCopyrightText: 2025 David Glick <david@glicksoftware.com>
#
# SPDX-License-Identifier: MIT

# This is loaded by ~horse_with_no_namespace.pth,
# which is loaded by Python's `site` module
# when it is installed in a site-packages folder.

# It's important that the .pth file starts with a tilde.
# This makes sure that it is loaded after other .pth files.
# (This is not guaranteed by Python,
# but the site module sorts the files before processing them,
# and that hasn't changed recently.)

import pkgutil
import os
import sys

logged = False

limit_namespaces = os.getenv("HORSE_WITH_NO_NAMESPACES")
if limit_namespaces is not None:
    limit_namespaces = set(limit_namespaces.split(","))

_message = (
    "🐎 This Python uses horse-with-no-namespace "
    "to make pkg_resources namespace packages compatible "
    "with PEP 420 namespace packages."
)

if limit_namespaces:
    _message += " It is limited to the following namespaces: " + ", ".join(
        limit_namespaces
    )


def apply():
    # The Python site module can call us more than once.
    # We need to actually do this the last time,
    # But we only want to show the notice once.
    global logged
    if not logged:
        print(_message, file=sys.stderr)
        logged = True

    # Only patch pkg_resources if it is installed...
    try:
        import pkg_resources
    except ImportError:
        pass
    else:
        # Patch pkg_resources.declare_namespace
        # to update __path__ using pkgutil.extend_path instead
        try:
            pkg_resources._original_declare_namespace
        except AttributeError:
            pkg_resources._original_declare_namespace = pkg_resources.declare_namespace

        def declare_namespace(packageName):
            if limit_namespaces:
                if (
                    not any(
                        packageName.startswith(prefix + ".")
                        for prefix in limit_namespaces
                    )
                    or packageName not in limit_namespaces
                ):
                    return pkg_resources._original_declare_namespace(packageName)

            if limit_namespaces:
                print(
                    f"🐎 Declaring namespace package {packageName} "
                    "using pkgutil.extend_path.",
                    file=sys.stderr,
                )
            parent_locals = sys._getframe(1).f_locals
            if not "__path__" in parent_locals:
                parent_locals["__path__"] = []
            parent_locals["__path__"] = pkgutil.extend_path(
                parent_locals["__path__"], packageName
            )

        pkg_resources.declare_namespace = declare_namespace

    # Remove existing namespace package modules that were already created
    # by other .pth files, possibly with an incomplete __path__
    for name, module in list(sys.modules.items()):
        if (
            limit_namespaces
            and not any(name.startswith(prefix + ".") for prefix in limit_namespaces)
            and name not in limit_namespaces
        ):
            continue

        if limit_namespaces:
            print(
                f"🐎 Removing existing namespace package {name} "
                "to ensure it is compatible with PEP 420.",
                file=sys.stderr,
            )
        loader = getattr(module, "__loader__", None)
        if loader and loader.__class__.__name__ == "NamespaceLoader":
            del sys.modules[name]
