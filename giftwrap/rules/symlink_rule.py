from .base import Rule


class SymlinkRule(Rule):
    """Adds symlink to the list of symlinks registered in the package.
    """

    def __init__(self, source, linkname):
        self._symlink = (source, linkname)

    def apply(self, package, context):
        context.symlinks += [self._symlink]
