=====================
Software Requirements
=====================

.. contents:: `Contents`
    :depth: 3
    :local:

---------------------------------
Requirements for mlx.traceability
---------------------------------

.. item:: RQT-TRACEABILITY A plugin for sphinx documentation system, adding traceability

    System shall implement a plugin for the sphinx documentation system. It shall add tracebility within
    the documentation.

.. item:: RQT-ITEMIZE Allow splitting the documentation in parts
    :depends_on: RQT-TRACEABILITY

    The plugin shall allow for splitting the documentation in parts.

.. item:: RQT-DOCUMENTATION_ID Identification of documentation part
    :depends_on: RQT-ITEMIZE

    A documentation part shall have a unique identification.

.. item:: RQT-CAPTION Brief description of documentation part
    :depends_on: RQT-ITEMIZE

    A documentation part shall have a optional brief description.

.. item:: RQT-CONTENT Content of documentation part
    :depends_on: RQT-ITEMIZE

    A documentation part shall have optional content. The content shall be parseable reStructuredText (RST), and passed
    through the configured sphinx parser/renderer.

.. item:: RQT-ATTRIBUTES Documentation parts can have attributes
    :depends_on: RQT-ITEMIZE

    It shall be possible to add attributes to the documentation parts.
    Attributes have a key and an optional value.
    The set of attributes and the validness of the attribute values shall be configurable.

.. item:: RQT-RELATIONS Documentation parts can be linked to each other
    :depends_on: RQT-ITEMIZE

    It shall be possible to link documentation parts to other documentation parts.
    The set of relations shall be configurable.

.. item:: RQT-AUTO_REVERSE Automatic creation of reverse relations
    :depends_on: RQT-RELATIONS

    When a documentation part <A> is related to a documentation part <B> (forward relation), the reverse
    relation from documentation part <B> to documentation part <A> shall be automatically created.

.. item:: RQT-LIST Listing documentation parts
    :depends_on: RQT-ITEMIZE

    It shall be possible to generate a list of documentation parts matching a certain query.

.. item:: RQT-COVERAGE Calculation of coverage for relations between documentation parts
    :depends_on: RQT-RELATIONS

    It shall be possible to calculate the coverage for a certain type of relation between
    documentation parts.

.. item:: RQT-MATRIX Auto-generation of a traceability matrix
    :depends_on: RQT-RELATIONS

    It shall be possible to query the relations between documentation parts.
    It shall be possible to generate overview matrix of these relations.

.. item:: RQT-TREE Auto-generation of a traceability tree
    :depends_on: RQT-RELATIONS

    It shall be possible to query the relations between documentation parts.
    It shall be possible to generate overview tree of these relations.

.. item:: RQT-ATTRIBUTES_MATRIX Overview of attributes on documentation parts
    :depends_on: RQT-ATTRIBUTES

    An overview table of the attribute values for documentation parts shall be generated.

.. item:: RQT-ATTRIBUTE_SORT Custom sorting of items' attributes
    :depends_on: RQT-ATTRIBUTES
    :fulfilled_by: DESIGN-ATTRIBUTE_SORT

    The plugin shall be able to allow configurability of the order of items' attributes.

.. item:: RQT-PERFORMANCE The plugin shall be performant
    :depends_on: RQT-TRACEABILITY
    :non_functional:

    The plugin shall be optimized for performance to minimize its impact on the documentation's build time.
    For example, unneeded sorting should be avoided.

.. item:: RQT-DUMMY Dummy requirement that is not covered by a test
    :fulfilled_by: DESIGN-ATTRIBUTES DESIGN-ITEMIZE

-------------------
Traceability matrix
-------------------

Tree of requirements
====================

.. item-tree:: Requirement tree
    :top: RQT
    :top_relation_filter: depends_on
    :type: impacts_on

Design coverage
===============

.. item-matrix:: Trace requirements to design
    :source: RQT
    :target: DESIGN
    :sourcetitle: Requirement
    :targettitle: Design
    :stats:

.. item-piechart:: Design coverage chart of functional requirements
    :id_set: RQT DESIGN
    :label_set: Uncovered, Covered
    :functional: .*
    :sourcetype: fulfilled_by

Test coverage
=============

.. item-matrix:: Trace requirements to test cases
    :source: RQT
    :target: [IU]TEST
    :sourcetitle: Requirement
    :targettitle: Test case
    :nocaptions:
    :stats:

.. item-matrix:: Trace requirements to test case reports
    :source: RQT
    :intermediate: [IU]TEST
    :target: [IU]TEST_REP
    :targetcolumns: result
    :type: validated_by | passed_by skipped_by failed_by
    :splitintermediates:
    :sourcetitle: Requirement
    :intermediatetitle: Test case
    :targettitle: Test case report
    :nocaptions:
    :stats:

.. item-piechart:: Chart fetching third label from defaults
    :id_set: RQT [IU]TEST [IU]TEST_REP
    :label_set: not covered, covered
    :colors: orange c b

.. item-piechart:: Test coverage chart targeting UTEST and ITEST
    :id_set: RQT [IU]TEST [IU]TEST_REP
    :label_set: not covered, covered
    :colors: orange c b darkred green yellow
    :targettype: failed_by passed_by skipped_by

.. item-piechart:: Test coverage chart targeting ITEST only
    :id_set: RQT ITEST ITEST_REP
    :label_set: not covered, covered
    :colors: orange c b darkred green yellow
    :targettype: failed_by passed_by skipped_by

.. item-piechart:: Test coverage chart with test results, based on the :result: attribute
    :id_set: RQT [IU]TEST [IU]TEST_REP
    :sourcetype: validated_by
    :targettype: failed_by passed_by skipped_by
    :label_set: uncovered, covered, has report
    :result: ERROR, fail, pass
    :colors: orange c b darkred #FF0000 g pink

..
    uncovered: orange (orange)
    covered: c (cyan)
    ran test: b (blue)
    ERROR: darkred (dark red)
    fail: #FF0000 (red)
    pass: g (green)

.. item-piechart:: Test coverage chart with test results, based on the :targettype: option
    :id_set: RQT [IU]TEST [IU]TEST_REP
    :label_set: uncovered, covered, ran test
    :sourcetype: validated_by
    :targettype: failed_by passed_by skipped_by
    :colors: orange c b r g y

.. item-piechart:: Test coverage chart with test results, based on the :targettype: option (in bad order)
    :id_set: RQT [IU]TEST [IU]TEST_REP
    :label_set: uncovered, covered, ran test
    :sourcetype: validated_by
    :targettype: skipped_by passed_by failed_by
    :colors: orange c b y g r

.. item-piechart:: Test cases as source using sourcetype to label with the :splitsourcetype: flag
    :id_set: [IU]TEST [IU]TEST_REP WAIVER
    :label_set: not executed, unused, expected failure
    :sourcetype: failed_by passed_by skipped_by
    :status: not implemented,
    :colors: orange black cyan r g y slategrey
    :splitsourcetype:

.. item-piechart:: All uncovered as the bad sourcetype results in 0 links
    :id_set: RQT [IU]TEST
    :sourcetype: impacts_on

.. item-piechart:: All uncovered as there is no direct relationship
    :id_set: [IU]TEST_REP RQT
    :label_set: uncovered, covered
    :colors: orange c

.. item-piechart:: Chart with only one color configured to trigger warning
    :id_set: RQT [IU]TEST [IU]TEST_REP
    :label_set: not covered, covered
    :colors: slategrey

.. item-piechart:: Chart without any items: no image or warning shall be generated
    :id_set: NONEXISTENT [IU]TEST
