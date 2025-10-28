#! /bin/bash

set -e

GMPURL=https://ftp.gnu.org/gnu/gmp/
GMPVERSION=gmp-6.3.0

if [ ! $(uname) = "Darwin" ] ; then
    echo "This script configured for macOS only"
    exit 1
fi
    
if [[ $(pwd) =~ " " ]]; then
    echo "Fatal Error: Sorry, the path:"
    echo "             $(pwd)"
    echo "             has a space in it, preventing GMP from building"
    echo "             because of a limitation of libtool."
    exit 1
fi

echo Building gmp ...


if [ ! -e ${GMPVERSION}.tar.bz2 ] ; then
    echo "Downloading GMP source archive ..." ;
    curl -O ${GMPURL}${GMPVERSION}.tar.bz2 ;
fi
if [ ! -e gmp_src ] ; then
    echo "Extracting gmp source code ..."
    tar xjf ${GMPVERSION}.tar.bz2
    mv ${GMPVERSION} gmp_src
fi
cd gmp_src
export ABI=64
if /usr/bin/machine | grep arm > /dev/null ; then
    BUILD_SYSTEM=arm64-none-darwin
    export CFLAGS="-mmacosx-version-min=11.0"    
else
    BUILD_SYSTEM=x86_64-none-darwin
    export CFLAGS="-mmacosx-version-min=10.9 -mno-avx2 -mno-bmi2"
fi
echo $BUILD_SYSTEM
# Use the old linker for x86_64 to avoid a spurious "branch8 out of range" error.
if [ `/usr/bin/ld -ld_classic 2> >(grep -c warning)` != "0" ] ; then
    export LDFLAGS="-ld_classic"
fi


./configure --enable-cxx --with-pic --build=${BUILD_SYSTEM} --prefix=$(pwd)/local
make install
ln -s -F $(pwd)/local/lib/* ../extlib/
ln -s -F $(pwd)/local/include/* ../extinclude/
