Using overrides
---------------

Default fixes and overrides are located in ``burst/providers/definitions.py``,
and although you can edit that file directly, keep in mind that you will lose
your changes on the next update. You can override existing definitions by adding
another file named ``overrides.py`` in your `userdata`_ folder under
``addon_data/script.quasar.burst``. Put all your overrides in the ``overrides``
variable within that file, as such:

.. code-block:: js

    overrides = {
        'torlock': {
            'name': 'MyTorLock'
        },
        'freshon.tv': {
            'tv_keywords': '{title} s{season:2}e{episode:2}'
        }
    }

.. _userdata: http://kodi.wiki/view/Userdata
