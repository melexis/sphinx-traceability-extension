==========
Unit Tests
==========

.. contents:: `Contents`
    :depth: 3
    :local:

-------------------------------
Unit Tests for mlx.traceability
-------------------------------

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
    :validates: RQT-CAPTION

.. item-link::
    :sources: RQT-ATTRIBUTES_FAKE
    :targets: UTEST_TRACEABLE_COLLECTION-GET_ITEMS_ATTRIBUTE
    :type: validated_by

.. item-relink::
    :remap: RQT-ATTRIBUTES_FAKE
    :target: RQT-ATTRIBUTES
    :type: validates
