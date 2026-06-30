.. highlight:: shell

============
Contributing
============

Contributions are welcome and greatly appreciated! Every little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Reporting of Bugs and Defects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A defect is any variance between actual and expected result, this can include bugs in the code or defects in the documentation or visualization.

Please report defects to the `the GitHub Tracker <https://github.com/heremaps/here-qgis-python/issues>`_
using the **Defect** description template.

`Pull Request Guidelines`_ for details on best developmental practices.

Features
~~~~~~~~

If you wish to propose a feature, please file an issue on `the GitHub Tracker <https://github.com/heremaps/here-qgis-python/issues>`_ using the **Feature** description template. Community members will help refine and design your idea until it is ready for implementation.
Via these early reviews, we hope to steer contributors away from producing work outside of the project boundaries.

Please see the `Pull Request Guidelines`_ for details on best developmental practices.

Documentation
~~~~~~~~~~~~~

HERE QGIS Python Library could always use more documentation, whether as part of the official HERE QGIS Python Library docs, in docstrings, tutorials and even on the web in blog posts, articles and such.

For docstrings, please use the `google style docstring format <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

Working on issues
------------------

After an issue is created, the progress of the issues is tracked on the `GitHub issue board <https://github.com/heremaps/here-qgis-python>`_.
The maintainers will update the state using `labels <https://github.com/heremaps/here-qgis-python/labels>`_ .
Once an issue is ready for review a Pull Request can be opened.



Pull Request Guidelines
--------------------------

Please create pull requests into the *develop* branch (not the *master* branch). Each request should be self-contained and address a single issue on the tracker.

Before you submit a pull request (PR), check that it meets these guidelines:

1. New code should be fully tested; running pytest in coverage mode can help identify gaps.
2. Documentation is updated, this includes docstrings and any necessary changes to existing tutorials, user documentation and so forth. We use the `google style docstring format <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.
3. The CI pipelines should pass for all pull requests.

   - Check the status of the pipelines, the status is also reported in the pull request.
   - pre-commit linter should pass.
   - All tests should pass.
   - No degradation in code coverage.
   - Documentation should build.
4. Ensure your pull request contains a clear description of the changes made and how it addresses the issue. If useful, add a screenshot to showcase your work to facilitate an easier review.

Congratulations! The maintainers will now review your work and suggest any necessary changes.
If no changes are required, a maintainer will "approve" the review.

Thank you very much for your hard work in improving HERE QGIS Python Library.
