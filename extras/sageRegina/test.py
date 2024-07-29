from __future__ import print_function

#__all__ = ['runTests']

from .. import __dict__ as reginaDict
from . version import version

import sys
import os
import re
import glob
import difflib
import traceback
from io import StringIO

base_path = os.path.split(__file__)[0]
testsuite_path = os.path.join(base_path, 'testsuite')

def runSource(source):

    original_stdout = sys.stdout
    original_displayhook = sys.displayhook
    original_argv = sys.argv

    fakeout = StringIO()
    
    sys.stdout = fakeout
    sys.displayhook = sys.__displayhook__
    sys.argv = ['regina', testsuite_path]

    try:
        globs = reginaDict.copy()

        class ReginaWrapper:
            pass
        reginaWrapper = ReginaWrapper()
        reginaWrapper.__dict__ = reginaDict.copy()
        globs['regina'] = reginaWrapper

        exception_info = None
        try:
            exec(source, globs)
        except:
            exception_info = sys.exc_info()

    finally:
        sys.stdout = original_stdout
        sys.displayhook = original_displayhook
        sys.argv = original_argv

    return fakeout.getvalue(), exception_info

def runFile(path):
    return runSource(open(path).read())

def findTests():
    search_path = os.path.join(testsuite_path, '*.test')
    return [
        (os.path.splitext(os.path.basename(path))[0], path)
        for path in glob.glob(search_path)]

def runTest(testName, testFile):
    failed = ""
    
    output, exception_info = runFile(testFile)

    baseline = open(testFile.replace('.test', '.out')).read()

    if testName == 'misc':
        # Last line is about open function which displays
        # differently on different sytems, e.g., something like
        # <boost.python.function at 0x34534345345>
        output   = '\n'.join(  output.split('\n')[:-2])
        baseline = '\n'.join(baseline.split('\n')[:-2])

    if testName == 'docstrings':
        output = re.subn(r'(\s*)__pybind11_module_local_([a-zA-Z0-9_-]+) = <capsule.*\.\.\.',
                         r'\1__pybind11_module_local__ = ...', output)[0]
        output = re.subn(r'(\s*)Methods( inherited from pybind11_object:)',
                         r'\1Static methods\2', output)[0]
        output = re.subn(r'__new__\(\*args, \*\*kwargs\) class method of pybind11_builtins.pybind11_object',
                         r'__new__(*args, **kwargs) from pybind11_builtins.pybind11_type',
                         output)[0]

    # For Python 3.12, there are trailing whitespace issues, so we
    # normalize.
    baseline = [line.strip() for line in baseline.split('\n')]
    output = [line.strip() for line in output.split('\n')]
    if output != baseline:
        failed += "Difference between baseline and output:\n"
        failed += '\n'.join(
            difflib.context_diff(
                baseline,
                output,
                fromfile = os.path.basename(testFile),
                tofile = 'OUTPUT'))

    if exception_info:
        exception_type, exception, traceback_object = (
            exception_info)
        failed += "Raised exception: %s\n" % exception_type
        failed += "Exception detail: %s\n" % exception
        failed += "Trace:\n %s\n" % traceback.format_tb(traceback_object)

    return failed

def runTests():
    print("Testing Regina " + version)
    failedTests = []
    
    for testName, testFile in findTests():
        print("Running test %s:" % (testName + (20 - len(testName)) * " "),
              end = ' ')
        sys.stdout.flush()

        failureOutput = runTest(testName, testFile)

        if failureOutput:
            failedTests.append(testName)
            print("FAILED!!!")
            print(failureOutput)
        else:
            print("ok")
    
    if failedTests:
        print("The following %d test(s) failed: %s" % (
                len(failedTests), ', '.join(failedTests)))
    else:
        print("All tests passed for Regina " + version)

    return not failedTests

