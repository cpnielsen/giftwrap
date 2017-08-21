import os
from .base import Rule


class SymlinkRule(Rule):
    """Adds symlink to the list of symlinks registered in the package.
    """

    def __init__(self, source, linkname):
        self._source = source
        self._linkname = linkname

    def apply(self, package, context):
        source_dir = context.data_dir_path(
            os.path.dirname(self._source)
        )

        os.symlink(
            os.path.join(source_dir, os.path.basename(self._source)),
            os.path.basename(self._linkname)
        )
