from .base import Rule


class SymlinkRule(Rule):
    """Adds symlink to the list of symlinks registered in the package.
    """

    def __init__(self, symlink, target):
        self._symlink = "%s %s" % (symlink, target)

    def apply(self, package, context):
        context.symlinks += [self._symlink]
