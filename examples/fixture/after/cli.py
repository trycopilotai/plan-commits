import sys

from slugify import slugify


def main(argv):
    for arg in argv[1:]:
        print(slugify(arg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
