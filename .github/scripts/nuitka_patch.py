import sys

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: nuitka_patch.py <DependsExe.py>")

    path = sys.argv[1]
    with open(path, "r") as handle:
        lines = handle.readlines()

    with open(path, "w") as handle:
        handle.write(
            "try:\n"
            "    from nuitka.utils.OrderedSets import OrderedSet\n"
            "except ImportError:\n"
            "    try:\n"
            "        from nuitka.containers.OrderedSets import OrderedSet\n"
            "    except ImportError:\n"
            "        class OrderedSet(set): pass\n"
        )
        skip = False
        for line in lines:
            if "def detectDLLsWithDependencyWalker(" in line:
                handle.write(line)
                handle.write("    return OrderedSet()\n")
                skip = True
            elif skip and line.startswith("def "):
                skip = False
                handle.write(line)
            elif not skip:
                handle.write(line)

if __name__ == "__main__":
    main()
