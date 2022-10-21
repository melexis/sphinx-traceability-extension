==========
Unit Tests
==========

.. contents:: `Contents`
    :depth: 3
    :local:

-------------------------------
Unit Tests for mlx.traceability
-------------------------------

.. test item-link defined before item-relink and item definitions: item-link shall always be processed first

.. item-relink::
    :remap: RQT-ATTRIBUTES_FAKE
    :target: RQT-ATTRIBUTES
    :type: validates

.. item-link::
    :sources: RQT-ATTRIBUTES_FAKE
    :targets: UTEST_TRACEABLE_COLLECTION-GET_ITEMS_ATTRIBUTE
    :type: validated_by

.. duplicate item-link shall only result in a warning

.. item-link::
    :sources: RQT-ATTRIBUTES_FAKE
    :targets: UTEST_TRACEABLE_COLLECTION-GET_ITEMS_ATTRIBUTE
    :type: validated_by

.. item:: UTEST_TRACEABLE_ITEM-INIT
    :validates: RQT-DOCUMENTATION_ID

.. item:: UTEST_TRACEABLE_ITEM-SET_CAPTION
    :validates: RQT-CAPTION

.. item:: UTEST_TRACEABLE_ITEM-ADD_ATTRIBUTE_OVERWRITE
    :validates: RQT-ATTRIBUTES_FAKE

.. item:: UTEST_TRACEABLE_ITEM-ADD_ATTRIBUTE_NO_OVERWRITE
    :validates: RQT-ATTRIBUTES

.. item:: UTEST_TRACEABLE_ITEM-REMOVE_INVALID_ATTRIBUTE
    :validates: RQT-ATTRIBUTES

.. item:: UTEST_TRACEABLE_ITEM-REMOVE_ATTRIBUTE
    :validates: RQT-ATTRIBUTES

.. item:: UTEST_TRACEABLE_ITEM-GET_ATTRIBUTES
    :validates: RQT-ATTRIBUTES_FAKE

.. item:: UTEST_TRACEABLE_ITEM-SET_CONTENT
    :validates: RQT-CONTENT

.. item:: UTEST_TRACEABLE_COLLECTION-GET_ITEMS_ATTRIBUTE
    :validates: RQT-ATTRIBUTES_MATRIX

.. item:: UTEST_TRACEABLE_COLLECTION-GET_ITEMS_SORTATTRIBUTES
    :validates: RQT-ATTRIBUTE_SORT RQT-ATTRIBUTES_MATRIX

.. item:: UTEST_TRACEABLE_COLLECTION-RELATED
    :validates: RQT-RELATIONS

.. item:: UTEST_ITEM_MATRIX-STORE_ROW
    :validates: RQT-MATRIX

.. item:: UTEST_ITEM_DIRECTIVE-MAKE_INTERNAL_ITEM_REF_SHOW_CAPTION

.. test item-relink defined after item-link and item definitions: item-link shall always be processed first

.. item-link::
    :sources: item_to_relink
    :targets: RQT-CAPTION
    :type: validates

.. item-relink::
    :remap: item_to_relink
    :target: UTEST_ITEM_DIRECTIVE-MAKE_INTERNAL_ITEM_REF_SHOW_CAPTION
    :type: validated_by

.. duplicate item-relink shall NOT result in a warning

.. item-relink::
    :remap: item_to_relink
    :target: UTEST_ITEM_DIRECTIVE-MAKE_INTERNAL_ITEM_REF_SHOW_CAPTION
    :type: validated_by

.. the placeholder item_to_relink shall not be removed from the collection:
   2 warnings shall be produced (1 per target)

.. item-link::
    :sources: item_to_relink
    :target: UTEST_TRACEABLE_ITEM-REMOVE_
    :type: trace

.. warn about invalid relation

.. item-relink::
    :remap: item_to_relink
    :target: UTEST_ITEM_DIRECTIVE-MAKE_INTERNAL_ITEM_REF_SHOW_CAPTION
    :type: non_existing_relation
