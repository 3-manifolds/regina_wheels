#!/usr/bin/env python3

# A packaging of Regina that allows easy installation using python's pip, see
# http://sageRegina.unhyperbolic.org/ for more information.
#
# Matthias Goerner, 09/24/2016
# enischte@gmail.com
#
# Run "python setup.py package" and it will automatically download all the
# necessary sources and create a tar ball suitable for pip.
#
# We can upload with "twine upload -r pypi sageRegina-...tar.gz"
# (Note that "twince register ..." is no longer necessary nor supported).
#
# TODO: extras/regina/engine/regina-config.h still needs to be updated
# manually to reflect REGINA/SNAPPY version.
# 
# Needed downgrade from boost 1.60 to boost 1.59 to not have
# missing to_python converter for NContainer.getFirstTreeChild()
#
# Error when GMP <= 5.1.3 and gcc >= 4.9:
# '::max_align_t' has not been declared
# see https://gcc.gnu.org/gcc-4.9/porting_to.html

# Get version from version.py and regina_dir from config.py,
# among other things.
exec(open('extras/sageRegina/version.py').read())
exec(open('extras/sageRegina/config.py').read())

import glob, os, sys, re, platform, subprocess

# Add an option which allows creating a wheel without rebuilding all of regina,
# for example after changing load paths in the regina library..
skip_build = False
if '--skip_build' in sys.argv:
    skip_build = True
    sys.argv.remove('--skip_build')

    # We can only build regina for macOS 10.15 and newer
if sys.platform == 'darwin':
    arch = platform.machine()
    os.environ['_PYTHON_HOST_PLATFORM'] = 'macosx-10.15-%s'%arch
    os.environ['ARCHFLAGS']='-arch %s'%arch
    
# Some of this is copied from SnapPy

# Without the next line, we get an error even though we never
# use distutils as a symbol
from setuptools import distutils

from distutils import sysconfig, log
from distutils.core import Extension
from setuptools import setup, Command

def recursive_glob(path, extension, depth = 0, predicate = None):
    """
    Find all files with the given extension under path up until
    the given depth (defaults to 0). If predicate is given, filter out
    results for which predicate returns False.
    """

    result = []
    for l in range(depth + 1):
        path_components = path.split('/') + l * ['*'] + ['*.' + extension]
        result += glob.glob(os.path.join(*path_components))

    if predicate:
        return [ file_path for file_path in result
                 if predicate(file_path) ]

    #if not result:
    #    raise Exception("No files to compile found. Something is wrong.")

    return result

try:
    import numpy
    numpy_include_paths = [ numpy.get_include() ]
except:
    numpy_include_paths = [ ]

def tokyocabinet_predicate(file_path):
    files_with_main = ['tcucodec.c', 'test.c']

    file_name = os.path.basename(file_path)

    return not (file_name in files_with_main)

platform_extra_compile_args = ['-O3']
platform_extra_link_args = []
if sys.platform == 'darwin':
    platform_extra_compile_args = ['-mmacosx-version-min=10.15']
    platform_extra_link_args = ['-Lextlib', '-liconv',
                                '-Wl,-exported_symbols_list,exported_symbols']
elif sys.platform.startswith('linux'):
    platform_extra_link_args = ['-s']

tokyocabinet_library = {
    'language' : 'c',
    'sources' : recursive_glob(tokyocabinet_dir, 'c',
                               predicate = tokyocabinet_predicate),
    'include_dirs' : [ tokyocabinet_dir ],
    'extra_compile_args' : [ '-std=gnu99' ] + platform_extra_compile_args
}

def libxml_predicate(file_path):

    file_name = os.path.basename(file_path)

    # Filter out files containing main and those supporting
    # xzlib since we don't need it.
    return not ((file_name in ['trio.c', 'xzlib.c']) or
                file_name.startswith('test') or
                file_name.startswith('run'))

libxml_library = {
    'language' : 'c',
    'sources' : recursive_glob(libxml_dir, 'c', predicate = libxml_predicate),
    'include_dirs' : [ libxml_dir + '/include', 'extras/libxml' ],
    # Not exactly sure what is going on with that THREAD_ENABLED, but
    # it didn't seem to build without
    'extra_compile_args' : ['-std=gnu99', '-DLIBXML_THREAD_ENABLED=1'] + platform_extra_compile_args
}

libraries = [
    ('tokyocabinet_regina', tokyocabinet_library),
    ('libxml_regina', libxml_library)
]

def check_dimension(file_name):
    """
    Returns false for files such as "Foo9.cpp" or "Foo10.cpp", ...
    
    Used to compile regina without high-dimension support
    (>8 dimensions).
    """

    if 'base64' in file_name:
        # Special case: base64.cpp
        return True

    dim_match = re.search(r'(\d+)\.', file_name)
    if not dim_match:
        return True
    dim = int(dim_match.group(1))
    return dim <= 8


def regina_predicate(file_path):
    library_path, file_name = os.path.split(file_path)
    library_name = os.path.basename(library_path)

    if 'syntax/' in file_path:
        # Syntax is only used by UI and sageRegina doesn't support UI (yet?)
        # Excluding it so that we don't need to pull in jansson
        return False

    if 'data/' in file_path:
        # Do not compile stuff in data
        return False

    if library_name == 'unused':
        return False

    if library_name == 'libnormaliz':
        # Normaliz needs special behavior.
        # libnormaliz-templated includes other .cpp files in that
        # directory which we should not include to avoid clashes

        file_name_base, ext = os.path.splitext(file_name)
        
        return not ('nmz_' in file_name_base)

    if library_name == 'tons':
        # Stuff that is no longer supported and needs to be reimplemented.
        return False

    return check_dimension(file_name)

def regina_python_predicate(file_path):
    library_path, file_name = os.path.split(file_path)

    if file_name == 'registerIntFromPyIndex.cpp':
        return False

    return check_dimension(file_name)

def library_include_dirs(libraries):
    return sum(
        [ library['include_dirs'] for name, library in libraries],
        [])

regina_extension = Extension(
    'regina.engine',
    sources = (
        recursive_glob(regina_dir + '/engine', 'cpp', depth = 2,
                       predicate = regina_predicate) +
        # Needed to be renamed .cpp for it to work
#        recursive_glob(regina_dir + '/engine/snappea/kernel', 'cpp') +
#        recursive_glob(regina_dir + '/engine/snappea/snappy', 'cpp') +
        recursive_glob(regina_dir + '/python', 'cpp', depth = 1,
                       predicate = regina_python_predicate)),
    include_dirs = [
            regina_dir + '/engine',
            regina_dir + '/python',
            'extras/regina/engine',
            'extinclude',
        ] + library_include_dirs(libraries),
    language = 'c++',
    extra_compile_args=(['-fpermissive', '-std=c++17'] + platform_extra_compile_args),
    libraries = ['gmp','gmpxx','m', 'bz2'],
    library_dirs = ['extlib'],

    # Adding bz2 to the libraries gives a command like 
    # g++ .... -lbz2 -lboost_iostreams_regina ...
    #
    # boost_iostreams_regina needs symbols from bz2 but g++ won't
    # link it unless -lbz2 follows -lboost_iostreams_regina
    #
    # Similarly for libxml and -lz.
    #
    # We achieve the right order by adding it to extra_link_args
    # instead.
    extra_link_args = ['-lz'] + platform_extra_link_args)


# Monkey patch build_clib.build_libraries so that it takes extra_compile_args
# like Extension does.

from distutils.command import build_clib
from distutils.errors import DistutilsSetupError

def my_build_libraries(self, libraries):
    for (lib_name, build_info) in libraries:
        sources = build_info.get('sources')
        if sources is None or not isinstance(sources, (list, tuple)):
            raise DistutilsSetupError(
                ("in 'libraries' option (library '%s'), " +
                 "'sources' must be present and must be " +
                 "a list of source filenames") % lib_name)
        sources = list(sources)

        log.info("building '%s' library", lib_name)

        # First, compile the source code to object files in the library
        # directory.  (This should probably change to putting object
        # files in a temporary build directory.)
        macros = build_info.get('macros')
        include_dirs = build_info.get('include_dirs')
        objects = self.compiler.compile(
            sources,
            output_dir=self.build_temp,
            macros=macros,
            include_dirs=include_dirs,
            debug=self.debug,
            extra_postargs = build_info.get('extra_compile_args'))
        
        # Now "link" the object files together into a static library.
        # (On Unix at least, this isn't really linking -- it just
        # builds an archive.  Whatever.)
        self.compiler.create_static_lib(objects, lib_name,
                                        output_dir=self.build_clib,
                                        debug=self.debug)

build_clib.build_clib.build_libraries = my_build_libraries

import setuptools.command.build_clib
setuptools.command.build_clib.build_clib.build_libraries = my_build_libraries

class SystemCommand(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        for cmd in self.system_commands:
            if os.system(cmd):
                raise Exception("When executing %s" % cmd)

class CompoundCommand(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        for cmd in self.commands:
            self.run_command(cmd)

class package_fix_version_regina_config(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        version_parts = version.split('.')
        major_version = version_parts[0]
        minor_version = version_parts[1]
        major_minor_version = major_version + "." + minor_version
        # Ignoring patch version

        replace_patterns = (
            ( '#define PACKAGE_STRING ',
              '"Regina %s"' % major_minor_version),
            ( '#define PACKAGE_VERSION ',
              '"%s"' % major_minor_version),
            ( '#define PACKAGE_VERSION_MAJOR ',
              '%s' % major_version),
            ( '#define PACKAGE_VERSION_MINOR ',
              '%s' % minor_version))

        config_file = regina_dir + '/engine/regina-config.h'

        with open(config_file, 'r') as f:
            lines = f.read().split('\n')
        matches = 0
        for i in range(len(lines)):
            for prefix, value in replace_patterns:
                if lines[i].startswith(prefix):
                    lines[i] = prefix + ' ' + value
                    matches += 1
            if lines[i].startswith('#define REGINA_INSTALL_XDG'):
                lines[i] = ''
        if matches != len(replace_patterns):
            raise Exception(
                "Patching version numbers in %s failed, "
                "expected %d matches, got %d." % (
                    config_file, matches, len(replace_patterns)))
        with open(config_file, 'w') as f:
            f.write('\n'.join(lines))

class package_download_tokyocabinet(SystemCommand):
    system_commands = ['cd /tmp; curl -O %s' % tokyocabinet_uri]

class package_download_libxml(SystemCommand):
    system_commands = ['cd /tmp; curl -O %s' % libxml_uri]
    
class package_download(CompoundCommand):
    commands = [
        'package_download_tokyocabinet',
        'package_download_libxml'
        ]

class package_untar_tokyocabinet(SystemCommand):
    system_commands = ['tar -xzf /tmp/%s' % tokyocabinet_uri.split('/')[-1]]

class package_untar_libxml(SystemCommand):
    system_commands = ['tar -xzf /tmp/%s' % libxml_uri.split('/')[-1]]

class package_untar(CompoundCommand):
    commands = [
        'package_untar_tokyocabinet',
        'package_untar_libxml'
        ]

class package_clone_regina(SystemCommand):
    system_commands = ['git clone %s regina_cloned' % (regina_uri)]

class package_fetch_regina(SystemCommand):
    system_commands = ['cd regina_*; git fetch']

class package_checkout_regina(SystemCommand):
    system_commands = [
        'rm -rf regina_0000000',
        'mv regina_cloned regina_0000000',
        'cd regina_0000000; git reset --hard',
        'cd regina_0000000; git checkout %s' % regina_hash,
        'mv regina_0000000 %s' % regina_dir
        ]

class package_patch_regina(SystemCommand):
    target_dir = 'legacy' if sys.version_info < (3, 12) else 'modern'
    system_commands = [
        'cd regina_*; cp preconfig/pypi_' + target_dir + '/regina-config.h engine/',
        'cd regina_*; git apply ../patches/regina.diff'
        ]

class package_retrieve_tokyocabinet(CompoundCommand):
    commands = [
        'package_download_tokyocabinet',
        'package_untar_tokyocabinet'
        ]

class package_retrieve_libxml(CompoundCommand):
    commands = [
        'package_download_libxml',
        'package_untar_libxml'
        ]

class package_retrieve_regina(CompoundCommand):
    commands = [
        'package_clone_regina',
        'package_checkout_regina',
        'package_patch_regina'
        ]

class package_retrieve(CompoundCommand):
    commands = [
        'package_retrieve_tokyocabinet',
        'package_retrieve_libxml',
        'package_retrieve_regina'
        ]

class package_extras_libxml(SystemCommand):
    system_commands = ['cp -r extras/libxml/* %s' % libxml_dir]

class package_extras_regina(SystemCommand):
    system_commands = ['cp -r extras/regina/* %s' % regina_dir]

class package_extras(CompoundCommand):
    commands = [
        'package_extras_libxml',
        'package_extras_regina'
        ]

class package_move_info(SystemCommand):
    system_commands = [
        'mv regina.egg-info/PKG-INFO .',
        'rm -rf regina.egg-info'
        ]

class package_info(CompoundCommand):
    commands = [
        'egg_info',
        'package_move_info'
        ]

class package_assemble(CompoundCommand):
    commands = [
        'package_retrieve',
        'package_extras',
        'package_fix_version_regina_config',
        'package_info'
        ]

version_name = 'regina-%s' % version

class package_tar(SystemCommand):
    if 'linux' in sys.platform:
        transform_op = '--transform '
    else:
        # Mac
        transform_op = '-'
        
    system_commands = [
        ('COPYFILE_DISABLE=1 '
         'tar -czf %s.tar.gz '
         '%ss/./%s/ '
         '--exclude "*.tar.*" '
         '--exclude ".git" '
         '--exclude "*~" '
         '--exclude "dist" '
         '--exclude "build" '
         '--exclude "*.egg-info" '
         '.') % (version_name, transform_op, version_name)
        ]

class package(CompoundCommand):
    commands = [
        'package_assemble',
        'package_tar'
        ]

from distutils.command.build import build

class ReginaBuild(build):
    def run(self):
        build.run(self)
        if sys.platform == 'darwin' and arch == 'arm64':
            # On macOS we need to copy the gmp libraries into the package and
            # set the load paths in the regina library to @loader_path/<library name>
            # We assume that the fat gmp libraries reside in the extlib directory.
            # The delocate package can handle this for an intel build, and cibuildwheel
            # apparently does that, but our CI runners do not provide fat versions
            # of the gmp libraries and currently there still are no arm CI runners.
            regina_pkg_dir = os.path.join(self.build_lib, 'regina')
            gmplibs = glob.glob('extlib/libgmp*.*.dylib')
            engine = glob.glob(os.path.join(regina_pkg_dir, 'engine*'))[0]
            # Copy libraries into the package
            for lib in gmplibs:
                subprocess.run(['cp', lib, regina_pkg_dir])
            # Fix up the load paths.
            for lib in gmplibs:
                oldlib = os.path.join('@rpath', os.path.basename(lib))
                newlib = os.path.join('@loader_path', os.path.basename(lib))
                subprocess.run(['install_name_tool', '-change', oldlib, newlib, engine])
            # Re-sign the regina library, since changing the load paths breaks the
            # signature.  This can be done with a self-signed certificate, but must
            # be done for arm_64 libraries.
            try:
                with open('DEV_ID') as id_file:
                    DEV_ID = id_file.read().strip()
                    subprocess.run(['codesign', '-v', '-s', DEV_ID, '--timestamp',
                    '--options', 'runtime', '--entitlements', 'entitlement.plist',
                    '--force', os.path.join(regina_pkg_dir, engine)])
            except:
                pass
        # On linux, this is presumably handled by cibuildwheel.

from wheel.bdist_wheel import bdist_wheel

class ReginaBuildWheel(bdist_wheel):
    def run(self):
        self.skip_build = skip_build
        bdist_wheel.run(self)

cmdclass = {
    'build' : ReginaBuild,
    'bdist_wheel': ReginaBuildWheel,
    'package_download_tokyocabinet' : package_download_tokyocabinet,
    'package_download_libxml' : package_download_libxml,
    'package_download' : package_download,
    'package_untar_tokyocabinet' : package_untar_tokyocabinet,
    'package_untar_libxml' : package_untar_libxml,
    'package_untar' : package_untar,
    'package_clone_regina' : package_clone_regina,
    'package_fetch_regina' : package_fetch_regina,
    'package_checkout_regina' : package_checkout_regina,
    'package_patch_regina' : package_patch_regina,
    'package_retrieve_tokyocabinet': package_retrieve_tokyocabinet,
    'package_retrieve_libxml': package_retrieve_libxml,
    'package_retrieve_regina': package_retrieve_regina,
    'package_retrieve': package_retrieve,
    'package_extras_regina' : package_extras_regina,
    'package_extras_libxml' : package_extras_libxml,
    'package_extras' : package_extras,
    'package_move_info' : package_move_info,
    'package_info' : package_info,
    'package_fix_version_regina_config' : package_fix_version_regina_config,
    'package_assemble' : package_assemble,
    'package_tar' : package_tar,
    'package' : package}

setup(name = 'regina',
      version = version,
      zip_safe = False,
      description = 'Regina-Normal',
      python_requires = '>=3.6',
      long_description=open('README.rst').read(),
      long_description_content_type='text/x-rst',
      keywords = 'triangulations, topology',
      classifiers = [
           'Development Status :: 3 - Alpha',
           'Intended Audience :: Science/Research',
           'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
           'Operating System :: POSIX :: Linux',
           'Operating System :: MacOS :: MacOS X',
           'Programming Language :: C',
           'Programming Language :: C++', 
           'Programming Language :: Python',
           'Programming Language :: Cython',
           'Topic :: Scientific/Engineering :: Mathematics',
      ],
      author = 'The Regina developers, Marc Culler, Nathan Dunfield, and Matthias Goerner',
      author_email = 'snappy-help@computop.org',
      url = 'http://github.com/3-manifolds/regina_wheels',
      license='GPLv2+',
      packages = [
          'regina',
          'regina/pyCensus',
          'regina/sageRegina',
          'regina/sageRegina/testsuite' ],
      package_dir = {
          # For the __init__.py file from regina which imports
          # regina.engine
          'regina' : regina_dir + '/python/regina',
          'regina/pyCensus' : regina_dir + '/python/regina/pyCensus',
          'regina/sageRegina' : 'extras/sageRegina',
          'regina/sageRegina/testsuite' : regina_dir + '/python/testsuite'
      },
      package_data = {
          'regina/sageRegina/testsuite' : ['*.*'],
          'regina/pyCensus' : ['*.tdb'],
      },
      ext_modules = [ regina_extension ],
      libraries = libraries,
      cmdclass = cmdclass)
