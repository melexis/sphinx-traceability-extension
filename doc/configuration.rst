.. _traceability_config:

=============
Configuration
=============

In your Sphinx project's ``conf.py`` file, add ``mlx.traceability`` to the list of enabled extensions:

.. code-block:: python

    extensions = [
        ...
        'mlx.traceability',
    ]

.. _traceability_config_attributes:

----------------
Valid attributes
----------------

Python variable *traceability_attributes* can be defined in order to override the
default configuration of the traceability plugin.
It is a *dictionary* of attribute pairs: the *key* is the name of the attribute (can only be lowercase),
while the *value* holds the regular expression to which the attribute-value should comply.

Example of attributes and their regular expression:

.. code-block:: python

    traceability_attributes = {
        'value': '^.*$',
        'asil': '^(QM|[ABCD])$',
        'non_functional': '^.{0}$',  # empty string
    }

.. _traceability_config_attribute2string:

-----------------------------
Stringification of attributes
-----------------------------

Python variable *traceability_attribute_to_string* can be defined in order to override the
default configuration of the traceability plugin.
It is a *dictionary* of attribute stringifications: the *key* is the name of the attribute, while
the *value* holds the string representation (as to be rendered in html) of the attribute name.

Example of attribute stringification:

.. code-block:: python

    traceability_relationship_to_string = {
        'value': 'Value',
        'asil': 'ASIL',
    }

.. _traceability_config_relations:

-------------------
Valid relationships
-------------------

Python variable *traceability_relationships* can be defined in order to override the
default configuration of the traceability plugin.
It is a *dictionary* of relationship pairs: the *key* is the name of the forward relationship, while the *value* holds
the name of the corresponding reverse relationship. Both can only be lowercase.

Relationships with prefix *ext_* are treated in a different way: they are handled as external relationships and don't
need a reverse relationship.

Example of internal and external relationship pairs:

.. code-block:: python

    traceability_relationships = {
        'validates': 'validated_by',
        'ext_polarion_reference': '',
    }

.. _traceability_config_relation2string:

--------------------------------
Stringification of relationships
--------------------------------

Python variable *traceability_relationship_to_string* can be defined in order to override the
default configuration of the traceability plugin.
It is a *dictionary* of relationship stringifications: the *key* is the name of the (forward or reverse) relationship,
while the *value* holds the string representation (as to be rendered in html) of the relationship.

Example of internal and external relationship stringification:

.. code-block:: python

    traceability_relationship_to_string = {
        'validates': 'Validates',
        'validated_by': 'Validated by',
        'ext_polarion_reference': 'Polarion reference',
    }

.. _traceability_config_ext2url:

----------------------------------------
External relationship to URL translation
----------------------------------------

External relationships need to be translated to URL's while rendering. For each defined external relationship,
an entry in the *dictionary* named *traceability_external_relationship_to_url* is needed. The URL generation
is templated using the *fieldN* keyword, where N is a number incrementing from 1 onwards for each value in the URL
that needs to be replaced.

Example configuration of URL translation of external relationship using 2 fields:

.. code-block:: python

    traceability_external_relationship_to_url = {
        'ext_polarion_reference': 'https://melexis.polarion.com/polarion/#/project/field1/workitem?id=field2',
    }

.. _traceability_config_render_relations:

---------------------------------------------------
Rendering of relationships per documentation object
---------------------------------------------------

When rendering the documentation objects, the user has the option to include/exclude the rendering of the
relationships to other documentation objects. This can be done through the Python variable
*traceability_render_relationship_per_item* which is *boolean*: a value of ``True`` will enable rendering
of relationships per documentation object, while a value of ``False`` will disable this rendering.

Example configuration of enable rendering relationships per item:

.. code-block:: python

    traceability_render_relationship_per_item = True

------------------------------------------------
Rendering of attributes per documentation object
------------------------------------------------

The rendering of attributes of documentation objects can be controlled through the *boolean* variable
*traceability_render_attributes_per_item*: rendering of attributes is enabled by setting it to ``True`` (the default)
while a value of ``False`` will prevent the attribute list from being rendered.

Example configuration of disabling per item attribute rendering:

.. code-block:: python

    traceability_render_attributes_per_item = False

-------------------------------------------------------------------------------------
Ability to collapse the list of relationships and attributes per documentation object
-------------------------------------------------------------------------------------

A button is added to each documentation object that has rendered relationships and/or attributes to be able to show and
hide these traceability links. The *boolean* configuration variable *traceability_collapse_links* allows selecting
between hiding and showing the list of links for all items on page load: setting its value to ``True`` results in the
list of links being hidden (collapsed) on page load, while the default value of ``False`` results in the list being
shown (uncollapsed). When an item is selected, its list will always be shown.

Example configuration of hiding the traceability links on page load:

.. code-block:: python

    traceability_collapse_links = True

.. _traceability_config_no_captions:

-----------
No captions
-----------

By default, the output will contain hyperlinks to all related items. By default, the caption for the target
item is displayed for each of the related items. The captions can be omitted at configuration level (see
this section) and at directive level (see e.g. :ref:`traceability_usage_item_matrix`).

No captions for item
====================

Example configuration of disabling the rendering of captions on item:

.. code-block:: python

    traceability_item_no_captions = True

No captions for item-list
=========================

Example configuration of disabling the rendering of captions on item-list:

.. code-block:: python

    traceability_list_no_captions = True

No captions for item-matrix
===========================

Example configuration of disabling the rendering of captions on item-matrix:

.. code-block:: python

    traceability_matrix_no_captions = True

No captions for item-attributes-matrix
======================================

Example configuration of disabling the rendering of captions on item-attributes-matrix:

.. code-block:: python

    traceability_attributes_matrix_no_captions = True

No captions for item-tree
=========================

Example configuration of disabling the rendering of captions on item-tree:

.. code-block:: python

    traceability_tree_no_captions = True

.. _traceability_config_export:

------
Export
------

The plugin allows exporting the documentation items.

Export to JSON
==============

As a preliminary test feature, the plugin allows to export the documentation items to a JSON database. The feature
can be enabled by setting the configuration to your JSON-file to export to. Note, the JSON-file is overwritten
(not appended) on every build of the documentation.

.. code-block:: python

    traceability_json_export_path = '/path/to/your/database.json'

As a preliminary feature, the database only contains per documentation item:

- the id
- the caption
- the document name and line number
- the attributes
- the relations to other items
- the MD5 hash of the content, which allows to check for changes in content when diffing 2 versions of the documentation

The actual content (RST content with images, formulas, etc) of the item is currently not stored.

.. note:: Requires sphinx >= 1.6.0

.. _traceability_config_callback:

----------------------------
Callback per item (advanced)
----------------------------

Callback to modify item
=======================

The plugin allows parsing and modifying documentation objects *behind the scenes* using a callback.
The callback function has this prototype:

.. code-block:: python

    traceability_callback_per_item = 'my_callback_per_item_func'

    def my_callback_per_item_func(name, collection):
        """Callback function called when an item-directive is being processed.

        Note: attributes, relationships and content (body) of the item can be modified. Sphinx processes each directive
        in turn, so attributes and relationships added or modified by other directives may not have been processed yet.

        Args:
            name (str): Name (id) of the item currently being parsed
            collection (TraceableCollection): Collection of all items that have been parsed so far
        """
        pass


.. note::

    The callback is executed while parsing the documentation item from your RST file. Note that not all items are
    available at the time this callback executes, the *collection* parameter is a growing collection of documentation
    objects.

.. note::

    **String-based configuration is recommended** because it allows Sphinx to properly cache and serialize the
    configuration. Using function objects directly will cause Sphinx to issue warnings about "unpickleable
    configuration values" and disable incremental builds.

Callback to inspect item
========================

To overcome the limitation of ``traceability_callback_per_item`` (see note above), a secondary callback function can be
defined. This function will be called when *rendering* each ``item``-directive. At that moment, all other directive
types, e.g. ``attribute-link`` and ``item-link``, will have been processed. You can use this callback function to detect
and warn about any gaps in your documentation but you cannot use it to make any modifications.
The callback function has this prototype:

.. code-block:: python

    traceability_inspect_item = 'my_inspect_item_func'

    def my_inspect_item_func(name, collection):
        """Callback function called when an item-directive is being rendered.

        Warning: the item cannot not be modified, only inspected.

        Note: At this stage of the documentation build, all directives, e.g. attribute-link and item-link,
        have been processed and any gaps in your documentation can be exposed by reporting a warning.

        Args:
            name (str): Name (id) of the item currently being parsed
            collection (TraceableCollection): Collection of all items that have been parsed so far
        """
        pass

.. warning::

    The collection should not be modified, only inspected. Modifying the collection in this step can corrupt it without
    triggering any warnings.

.. _traceability_optional_mandatory:

Example of requiring certain attributes on an item
==================================================

The callback function can modify traceable items, e.g. add attributes. In this example it reports a warning
when the item doesn't have either the `functional` or `non-functional` attribute defined *at the time its
``item``-directive is being processed*:

.. code-block:: python

    from mlx.traceability import report_warning

    def my_callback_per_item_func(name, collection):
        item = collection.get_item(name)
        if not (('functional' in item.attributes) ^ ('non_functional' in item.attributes)):
            report_warning("Requirement item {!r} must have either the 'functional' or 'non_functional' attribute; "
                           "adding 'functional'".format(name), docname=item.docname, lineno=item.lineno)
            item.add_attribute('functional', '')

    traceability_callback_per_item = 'my_callback_per_item_func'


.. _traceability_config_link_colors:

------------------------------
Custom colors for linked items
------------------------------

The plugin allows customization of the colors of traceable items in order to easily recognize the type of item which is
linked to. A dictionary in the configuration file defines the regexp, which is used to match_ item IDs, as key and a
tuple of 1-3 color defining strings as value. The first color is used for the default hyperlink state, the second color
is used for the hover and active states, and the third color is used to override the default color of the visited state.
Leaving a color empty results in the use of the default html style. The top regexp has the highest priority.

.. code-block:: python

    traceability_hyperlink_colors = {
        r'RQT|r[\d]+': ('#7F00FF', '#b369ff'),
        r'[IU]TEST_REP': ('rgba(255, 0, 0, 1)', 'rgba(255, 0, 0, 0.7)', 'rgb(200, 0, 0)'),
        r'[IU]TEST': ('goldenrod', 'hsl(43, 62%, 58%)', 'darkgoldenrod'),
        r'SYS_': ('', 'springgreen', ''),
        r'SRS_': ('', 'orange', ''),
    }

.. _traceability_notifications:

-------------------------------
Mapping of undefined references
-------------------------------

Undefined references can be mapped to a special item, e.g. to explain to the reader why the reference is undefined.
In the example below the special item has ID *DOC-NOTIFICATION*.

.. code-block:: python

    traceability_notifications = {
        'undefined-reference': 'DOC-NOTIFICATION',
    }


.. _traceability_default_config:

--------------
Default config
--------------

The plugin itself holds a default config that can be used for any traceability documenting project:

.. code-block:: python

    traceability_callback_per_item = None
    traceability_inspect_item = None
    traceability_attributes = {
        'value': '^.*$',
        'asil': '^(QM|[ABCD])$',
        'aspice': '^[123]$',
        'status': '^.*$',
        'result': '(?i)^(pass|fail|error)$'
        'attendees': '^([A-Z]{3}[, ]*)+$',
        'assignee': '^.*$',
        'effort': r'^([\d\.]+(mo|[wdhm]) ?)+$',
    }
    traceability_attribute_to_string = {
        'value': 'Value',
        'asil': 'ASIL',
        'aspice': 'ASPICE',
        'status': 'Status',
        'result': 'Result',
        'attendees': 'Attendees',
        'assignee': 'Assignee',
        'effort': 'Effort estimation',
    }
    traceability_attributes_sort = {
        'effort': 'natsort.natsorted',
    }
    traceability_relationships = {
        'fulfills': 'fulfilled_by',
        'depends_on': 'impacts_on',
        'implements': 'implemented_by',
        'realizes': 'realized_by',
        'validates': 'validated_by',
        'trace': 'backtrace',
        'ext_toolname': '',
    }
    traceability_relationship_to_string = {
        'fulfills': 'Fulfills',
        'fulfilled_by': 'Fulfilled by',
        'depends_on': 'Depends on',
        'impacts_on': 'Impacts on',
        'implements': 'Implements',
        'implemented_by': 'Implemented by',
        'realizes': 'Realizes',
        'realized_by': 'Realized by',
        'validates': 'Validates',
        'validated_by': 'Validated by',
        'trace': 'Traces',
        'backtrace': 'Backtraces',
        'ext_toolname': 'Reference to toolname',
    }
    traceability_external_relationship_to_url = {
        'ext_toolname': 'http://toolname.company.com/field1/workitem?field2',
    }
    traceability_render_relationship_per_item = False

This default configuration, which is built into the plugin, can be overridden through the conf.py of your project.

For Melexis.SWCC silicon projects, the SWCC process holds a default configuration in the *config/traceability_config.py*
file. For each of the above configuration variables, the default configuration file holds a variable with *swcc_*
prefix. Taking the default configuration is as easy as assiging the above configuration value with the *swcc_* variable.
Overriding a configuration is as easy as assigning your own values to a configuration value.

Example of accepting default configuration for relationships, while disabling (override) rendering of relationships
per documentation object:

.. code-block:: python

    sys.path.insert(0, os.path.abspath('<path_to_process_submodule>/config'))

    from traceability_config import swcc_traceability_attributes
    from traceability_config import swcc_traceability_relationships
    from traceability_config import swcc_traceability_relationship_to_string

    traceability_attributes = swcc_traceability_attributes
    traceability_relationships = swcc_traceability_relationships
    traceability_relationship_to_string = swcc_traceability_relationship_to_string
    traceability_render_relationship_per_item = False

.. _match: https://docs.python.org/3/library/re.html#re.match
