Self-contained Python packages of Regina
========================================

The program `Regina`_ is a powerful tool for studying low-dimensional
topology. It comes with a full `Python`_ interface that lets one
interact with it programmatically without writing any C++ code. Our
goal here is to provide self-contained binaries ("wheels") of Regina's
Python package that can be installed in seconds from Python's `PyPI`_
package repository using ``pip``.

It is offered for macOS (10.15 and newer) and Linux, but not
Windows. To try it out, do::

  python3 -m pip install --user --upgrade "regina>=7.0"
  python3 -m regina.test

On older versions of Linux, e.g. Ubuntu 18.04, you may need to update
``pip`` first via::

  python3 -m pip install --user --upgrade pip wheel

For more on using Regina in Python see the `main docs`_.

These binaries are produced and maintained by Marc Culler, Nathan
Dunfield, and Matthias Goerner, though of course 99.9% of the code and
credit is due to Ben Burton and the other authors of Regina
itself. This project evolved out of Goerner's `sageRegina`_
but works both with and without `SageMath`_. To install and test in
SageMath do the following in a terminal window::

  sage -pip install --user --upgrade "regina>=7.0"
  sage -python -m regina.test

One can also do this from **inside** SageMath (including from a
notebook) by::

  sage: %pip install --user "regina>=7.0"
  sage: import regina.test; regina.test.runTests()

Please report any technical problems via the `issue tracker`_ on the
`GitHub site`_ devoted to this repackaging of Regina.


Building from source
--------------------

If the available binaries do not work for you, you can try building
from source.  You will need have the development versions of the
libraries gmp, zlib, and bzip2 installed::

  git clone https://github.com/3-manifolds/regina_wheel
  cd regina_wheel
  python3 setup.py package_assemble
  python3 setup.py bdist_wheel
  python3 -m pip install dist/regina*.whl

This can easily take an hour or more.


License
-------

Copyright Ben Burton, Ryan Budney, William Pettersson, Marc Culler,
Nathan M. Dunfield, Matthias Goerner, and others 1999-present. This
code is released under the `GNU General Public License, version 2`_ or
(at your option) any later version as published by the Free Software
Foundation.

.. _Regina: https://regina-normal.github.io/
.. _Python: https://python.org
.. _PyPI: https://pypi.org
.. _main docs: https://regina-normal.github.io/#docs
.. _sageRegina: https://sageregina.unhyperbolic.org
.. _SageMath: https://sagemath.org
.. _issue tracker: https://github.com/3-manifolds/regina_wheels/issues
.. _GitHub site: https://github.com/3-manifolds/regina_wheels/
.. _GNU General Public License, version 2: https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
