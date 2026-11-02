.. _reference-state-guide:

Reference-State Management
===========================

Some detectors cannot decide from a static, pre-trained model alone: they need
to compare a new sample against a set of reference historical samples.
``tsmadkit`` supports this through a ``reference_state``: a folder that
:meth:`tsmadkit.AnomalyDetection.setup` keeps organized and up to date, so
that by the time ``detect()`` runs, those reference samples are ready to use
without recomputing anything.

Two Kinds of Files
------------------

A reference state manages two related sets of files, each tracked by its own
manifest:

- **History** is the raw reference data: one ``*.h5`` file per sample, each
  in the same ``time``/``values`` format described in :doc:`configuration`.
  The history manifest just records each file's name and hash.
- **Cache** is derived data, computed once per history sample so it does not
  need to be recomputed on every ``detect()`` call. Each cache file (``*.npz``)
  stores whatever your algorithm's ``transform()`` method returns for the
  matching history sample. The cache manifest records each cache file's hash
  together with the hash of the history file it was built from.

In short: history is the raw data you compare against, and cache is the
already-computed version of that data.

For example, a reference state built from two shots, ``1234`` and ``5678``,
looks like this on disk:

.. treeview::
  - :dir:`file` reference_state.json
  - :dir:`folder` history

    - :dir:`file` manifest.json
    - :dir:`file` 1234.h5
    - :dir:`file` 5678.h5

  - :dir:`folder` cache

    - :dir:`file` manifest.json
    - :dir:`file` 1234.npz
    - :dir:`file` 5678.npz

``history/manifest.json`` maps each raw sample to its hash:

.. code-block:: json

   {
       "1234.h5": "3fa2c9...",
       "5678.h5": "9c1eab..."
   }

``cache/manifest.json`` records, for each derived ``.npz`` file, which history
sample it was built from and that sample's hash at the time:

.. code-block:: json

   {
       "1234.npz": {
           "hash": "a8210e...",
           "depends_on": "../history/1234.h5",
           "dependency_hash": "3fa2c9..."
       },
       "5678.npz": {
           "hash": "b430f1...",
           "depends_on": "../history/5678.h5",
           "dependency_hash": "9c1eab..."
       }
   }

That ``dependency_hash`` is the link between the two folders: it is how
``setup()`` recognizes when a cache file is still valid, and when it needs to
be rebuilt from its history sample.

How History and Cache Stay in Sync
-----------------------------------

Recomputing every cache entry on every run would be wasteful, but serving a
stale cache entry (built from a history sample that has since changed) would
be wrong. ``setup()`` avoids both problems in two steps.

**Step 1: refresh the history manifest, if asked to.** The ``check`` mode in
the configuration controls this:

- ``check="fast"`` (the default) trusts ``history/manifest.json`` as it is,
  without re-hashing the ``*.h5`` files. This is the cheap path for normal
  runs, where the history folder has not changed since the manifest was last
  written.
- ``check="full"`` re-hashes every ``*.h5`` file in ``history/`` and rewrites
  the manifest from scratch. Use this after adding, removing, or editing raw
  history samples by hand, so those changes are actually picked up.

**Step 2: rebuild only the cache files that need it.** For each entry in the
(possibly just-refreshed) history manifest, ``setup()`` compares that entry's
hash against the ``dependency_hash`` recorded for the matching cache file. A
cache file is rebuilt, by calling your algorithm's ``transform()`` on that
history sample, only when:

- it is missing, or
- its recorded ``dependency_hash`` no longer matches its history sample's
  current hash, or
- the algorithm's name, version, or configuration changed since the
  reference state was last written (which invalidates the whole cache at
  once, since the meaning of ``transform()``'s output may have changed).
  The configuration is compared through its content hash, so reformatting
  the JSON file, passing the same content as a dictionary, or editing the
  ``reference_state`` section itself (e.g. switching ``check`` mode) does not
  count as a change.

Every other cache file is left untouched. Note that step 2 runs regardless of
``check`` mode: even a fast check still rebuilds cache files that are missing
or out of date, it just skips re-hashing history samples that a full check
would have caught changing silently on disk.

This is why adding historical comparison to a detector only requires one
extra method, ``transform(data: SignalSet) -> dict``: ``setup()`` calls it
once per history sample to populate the cache, and ``detect()`` can call it
again on the current sample to compute the same features for comparison.

.. _reference-state-from-scratch:

Starting From Scratch
----------------------

The first time ``setup()`` runs for a given reference state, none of the
files above exist yet: no ``reference_state.json``, no
``history/manifest.json``, no ``cache/manifest.json``. Nothing special needs
to be done for that case — it is just the trivial version of the two-step
algorithm above. A missing history manifest is treated the same as a stale
one, so ``setup()`` builds it from the ``*.h5`` files in ``history/``
regardless of ``check`` mode. A missing cache manifest means every history
sample looks new, so ``transform()`` runs once per sample to populate
``cache/`` and its manifest.

In practice, the setup you do by hand is:

1. Pick a directory for the reference state, say ``reference_state/``, and
   point the algorithm configuration's ``reference_state.path`` at a
   ``reference_state.json`` inside it. That file **does not** need to exist yet;
   its parent directory is what this guide calls ``<reference_state_dir>``:

   .. code-block:: json

      {
          "reference_state": {
              "path": "reference_state/reference_state.json",
              "check": "fast"
          }
      }

2. Create ``<reference_state_dir>/history/`` (``reference_state/history/`` in
   the example above) and put your raw ``*.h5`` samples directly in it.
3. Implement ``transform()``.
4. Call ``setup()`` once. That single call creates
   ``history/manifest.json``, ``cache/manifest.json`` (and the ``.npz``
   files behind it), and ``reference_state.json`` itself, all inside
   ``<reference_state_dir>``.

Do not hand-write any of the three JSON files; ``setup()`` generates all of
them.

Using the Cache in ``detect()``
--------------------------------

Once ``setup()`` has run, the cache entries are loaded, stacked one row per
history sample, and exposed as ``self.cache_data``: a dict keyed by whatever
fields your ``transform()`` returns. A typical ``detect()`` transforms the
current sample the same way and compares the result against
``self.cache_data``.

Where to Go Next
-----------------

- :ref:`reference-state-section` in :doc:`configuration` for the exact JSON
  keys and path conventions.
- :doc:`create-algorithm` for a runnable ``transform()``/``detect()`` example.
- :doc:`/algorithms/generated/ech_collector` for a real algorithm built this way.
