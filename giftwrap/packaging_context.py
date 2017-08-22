import os
import tempfile
from .utilities import (
    mkdirp, write_to_file, write_lines_to_file, ar_create, targz, run,
    glob_dir, string_ending_in_period,
)


class PackagingContext(object):
    """Packaging context.

    Handles scoping of the packaging.
    """

    def __init__(self):
        """Import a packaging context.

        Sets up necessary directories etc.
        """

        self._root_path = tempfile.mkdtemp()
        self._data_path = os.path.join(self._root_path, 'data')
        self._control_path = os.path.join(self._root_path, 'control')

        os.mkdir(self._data_path)
        os.mkdir(self._control_path)

    def control_path(self, filename):
        """Get the path for a control file.

        :param path: Control file filename.
        :returns: the absolute file system path for the control file.
        """

        return os.path.join(self._control_path, filename)

    def _mkdirp(self, path, permissions=0755):
        """Recursively make directories and set permissions.

        :param path: Absolute file system path.
        :param permissions:
            default 0755, Permissions to apply to any directories below the
            data path.
        """

        mkdirp(path)

        subdir_paths = os.path.relpath(path,
                                       self._data_path).split('/')

        abs_subdir_path = self._data_path
        for subdir_path in subdir_paths:
            abs_subdir_path = os.path.join(abs_subdir_path,
                                           subdir_path)
            os.chmod(abs_subdir_path,
                     permissions)

    def data_path(self, path, permissions=0755):
        """Get the path for a data file or directory.

        Ensure that all directories have been created for the creation of a
        file at the given path.

        :param path: Absolute path in the package root filesystem.
        :param permissions:
            Permissions to apply to any directories below the root path.
        :returns: the absolute file system path for the given path.
        """

        abs_path = os.path.join(self._data_path,
                                path.lstrip('/'))
        self._mkdirp(os.path.dirname(abs_path),
                     permissions)

        return abs_path

    def data_dir_path(self,
                      path,
                      permissions=0755,
                      make_if_missing=True):
        """Get the path for a data directory.

        Ensures that the directory has been created.

        :param path: Absolute path in the package root filesystem.
        :param permissions:
            Permissions to apply to any directories below the root path.
        :param make_if_missing: Make directory if missing.
        :returns: the absolute file system path for the given path.
        """

        abs_path = os.path.join(self._data_path,
                                path.lstrip('/'))
        if make_if_missing:
            self._mkdirp(abs_path,
                         permissions)

        return abs_path

    def make_data_dir(self, path, user=None, group=None):
        """Make data directory.

        Ensures that the directory has been created.

        :param path: Absolute path in the package root filesystem.
        :returns: the absolute file system path for the given path.
        """

        abs_path = self.data_dir_path(path)

        if user is not None:
            self.postinst_commands += ['chown -R %s %s' % (
                ('%s:%s' % (user, group) if group is not None else user),
                path)]

        return abs_path

    def build(self, package):
        """Build the package in the temporary directories.
        """

        self.postinst_commands = []
        self.symlinks = []

        for rule in package.rules:
            rule.apply(package, self)

        # Create the control files.
        self._write_control(package)
        self._write_postinst(package)
        self._write_copyright(package)
        self._write_conffiles(package)
        self._write_symlinks(package)

    def _write_postinst(self, package):
        """Write the postinst file during the build process.
        """

        lines = ['#!/bin/sh',
                 '# postinst script generated by giftwrap.',
                 'set -e',
                 'case "$1" in',
                 '    configure)']

        lines += ['        %s' % (x) for x in self.postinst_commands]

        lines += ['    ;;',
                  '',
                  '    abort-upgrade|abort-remove|abort-deconfigure)',
                  '    ;;',
                  '',
                  '    *)',
                  '        echo "postinst called with unknown argument `$1`" >&2',
                  '        exit 1',
                  '    ;;',
                  'esac',
                  '',
                  'exit 0']

        write_lines_to_file(lines,
                            self.control_path('postinst'),
                            permissions=0755)

    def _write_control(self,
                       package,
                       control_binary=True):
        """Generate a control file.

        :param control_binary: default ``True``, Whether or not the generated
        file should represent a binary package. If ``False``, the control file
        will be for a source distribution package.
        """

        # Determine the architecture.
        if isinstance(package.architectures, list):
            architectures = package.architectures
        elif isinstance(package.architectures, tuple):
            architectures = list(package.architectures)
        elif isinstance(package.architectures, str):
            architectures = [package.architectures]
        else:
            # Hacky but it works for now.
            host_architecture = run(['dpkg', '--print-architecture'],
                                    vital=False)
            architectures = [host_architecture.strip()
                             if host_architecture is not None else 'any']

        if not control_binary and 'source' not in architectures:
            architectures.append('source')

        # Build the rules set based on availability.
        rules = {
            'Source': package.name,
            'Version': package.version,
            'Architecture': ' '.join(architectures),
            'Maintainer': '%s <%s>' % (package.maintainer_name,
                                       package.maintainer_email),
            'Description': '%s\n %s' % (
                string_ending_in_period(package.description),
                string_ending_in_period(package.long_description))
        }

        if package.homepage is not None:
            rules['Homepage'] = package.homepage

        if control_binary:
            rules['Package'] = package.name

        if package.section is not None:
            rules['Section'] = package.section

        if package.priority is not None:
            rules['Priority'] = package.priority

        if package.depends is not None and len(package.depends) > 0:
            rules['Depends'] = ', '.join(package.depends)

        if package.conflicts is not None and len(package.conflicts) > 0:
            rules['Conflicts'] = ', '.join(package.conflicts)

        # Finally, write the file.
        write_lines_to_file(['%s: %s' % (k, rules[k]) for k in rules],
                            self.control_path('control'))

    def _write_copyright(self,
                         package):
        """Write the copyright to the output directory.
        """

        write_to_file(package.copyright,
                      self.data_path('/usr/share/doc/%s/copyright' % (
                                     package.name)))

    def _write_conffiles(self,
                         package):
        """Write the configuration file to the output directory.
        """

        # List the configuration files.
        etc_path = self.data_dir_path('/etc',
                                      make_if_missing=False)
        conffiles = []

        for root, sub_folders, rel_files in os.walk(etc_path):
            for rel_file in rel_files:
                conffiles.append('/etc/%s' % os.path.relpath(
                                                os.path.join(root,
                                                             rel_file),
                                                etc_path))

        # Write the configuration files to the control file.
        write_lines_to_file(conffiles, self.control_path('conffiles'))

    def _write_symlinks(self, package):
        """Writes the symlinks to $mypackage links"""
        if self.symlinks:
            for source, linkname in self.symlinks:
                lname = os.path.join(self._data_path, linkname)
                print '%s <- %s (%s)' % (source, lname, linkname)
                os.symlink(source, lname)

    def pack(self,
             package,
             destination_path,
             run_lintian=False):
        """Pack the context to a Debian package.

        :param package: Package to pack.
        :param destination_path: Destination of the created package.
        :param run_lintian: default ``False``, whether or not to run Lintian
        to check the package after the package has been generated. If Lintian
        is not found, this parameter will be ignored.
        """

        data_tarball_path = os.path.join(self._root_path, 'data.tar.gz')
        control_tarball_path = os.path.join(self._root_path, 'control.tar.gz')

        # Compress the control and data directories.
        targz(control_tarball_path,
              self._control_path,
              glob_dir(self._control_path))

        targz(data_tarball_path,
              self._data_path,
              glob_dir(self._data_path))

        # Write the Debian binary archive specifier.
        debian_binary_path = os.path.join(self._root_path, 'debian-binary')

        with open(debian_binary_path, 'w') as debian_binary:
            debian_binary.write('2.0\n')
            debian_binary.close()

        # Create the final Debian archive.
        # - the debian-binary file must go before all others.
        # http://ubuntuforums.org/archive/index.php/t-1481153.html
        archive_paths = [debian_binary_path,
                         control_tarball_path,
                         data_tarball_path]

        run(('rm -f %s' % (destination_path)).split(' '))
        ar_create(destination_path,
                  archive_paths)

        # Run Lintian if requested and available.
        if run_lintian:
            run(['lintian',
                 '-v',
                 '--color', 'always',
                 '--pedantic',
                 destination_path])
