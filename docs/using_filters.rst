Using filters
-------------

If you go in the add-on's Advanced settings, you will notice an option named
``Additional keyword filters (comma separated)``. Enabling this option will
bring up three sub-settings: ``Accept``, ``Block`` and ``Require``. They all
expect the same kind of parameters, which is a comma-separated list of keywords
to respectively either accept, block or require. Although it's mostly
self-explanatory, let's go over each of them to fully understand how they
behave, and what kind of results you mind expect when using those settings.

Format
======
A comma-separated list is a standard way of defining multiple values. You can
include spaces between keywords for readability, and Burst will work just the
same. For example, those two settings will be equivalent: ``HEVC,H265`` vs
``HEVC, H265``. They will both be understood as a list with the values
``["HEVC", "H265"]``. Also note that uppercase or lowercase makes no
difference, so both ``hevc`` and ``HeVc`` in a result name would also be
considered a match.

The only special trick about the format of keywords is done by using
underscores (``_``), which tell Burst to make sure there is a space, dot, dash,
also an underscore, or other separator between your keyword and the other parts
of the result's name. For example, if you want to match ``ITA``, but not
``italian``, you would use ``_ITA_`` as your keyword, which would match names
like ``A.Movie.2017.ITA.720p`` but *not* ``A.Movie.2017.Italian.720p``. A
trailing underscore would also return a match, ie. ``A.Movie.720p.ITA``.
**Note that the `Require` keyword treats underscores literally**, so using
``_ITA_`` in `Require` would only match names like ``A.Movie_ITA_720p``.

Keyword types
=============
Accept
~~~~~~
The `Accept` setting will return results that include **any** of the keywords
you specify. For example, ``Italian, French`` will return results that either
include ``italian`` or ``french``.

Block
~~~~~
The `Block` setting will block results that include **any** of the keywords
you specify, and can be the most dangerous filter to use. For example, ``ITA``
would block every result that has ``ita`` anywhere in its name, regardless of
delimiters like dots and dashes, so if you're looking for a movie named
`My Inheritance`, you would get absolutely no result. For that reason, you
should usually always add underscores around `Block` keywords to make sure
there are delimiters around those keywords.

Require
~~~~~~~
The `Require` setting is also a dangerous filter to use, and will require
**all** the keywords you specify to be included in the result names. For
example, if you specify ``ITA, _FR_``, you would only get results that include
**both** ``ITA`` and ``FR`` (with delimiters), which will be very few if any.
It can however be a very useful setting to get only results that include your
preferred language.
