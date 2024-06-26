from unittest import TestCase

from mlx.traceability import traceability_exception as exception
from mlx.traceability import traceable_attribute as attribute
from mlx.traceability import traceable_item as dut


class TestTraceableItem(TestCase):
    docname = 'folder/doc.rst'
    identification = 'some-random$name\'with<\"weird@symbols'
    attribute_key1 = 'some-random-attribute-key'
    attribute_key2 = 'some-random-attribute-2key'
    attribute_regex = 'some-random-attribute value[12]'
    attribute_value1 = 'some-random-attribute value1'
    attribute_value2 = 'some-random-attribute value2'
    attribute_value_invalid = 'some-random-attribute value3'
    fwd_relation = 'some-random-forward-relation'
    rev_relation = 'some-random-reverse-relation'
    identification_tgt = 'another-item-to-target'

    def setUp(self):
        attr1 = attribute.TraceableAttribute(self.attribute_key1, self.attribute_regex)
        dut.TraceableItem.define_attribute(attr1)
        attr2 = attribute.TraceableAttribute(self.attribute_key2, self.attribute_regex)
        dut.TraceableItem.define_attribute(attr2)

    def test_init(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        item.self_test()
        self.assertEqual(self.identification, item.identifier)
        self.assertFalse(item.is_placeholder)
        self.assertIsNotNone(item.docname)
        self.assertEqual(0, item.lineno)
        self.assertIsNone(item.node)
        self.assertIsNone(item.caption)
        self.assertIsNone(item.content)

    def test_init_placeholder(self):
        item = dut.TraceableItem(self.identification, placeholder=True)
        item.set_location(self.docname)
        with self.assertRaises(exception.TraceabilityException) as err:
            item.self_test()
        self.assertEqual(err.exception.docname, self.docname)
        self.assertEqual(self.identification, item.identifier)
        self.assertTrue(item.is_placeholder)
        # Verify dict
        self.assertEqual({}, item.to_dict())

    def test_to_dict(self):
        txt = 'some short description'
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        item.caption = txt
        # Verify dict
        data = item.to_dict()
        self.assertEqual(self.identification, data['id'])
        self.assertEqual(txt, data['caption'])
        self.assertEqual(self.docname, data['document'])
        self.assertEqual(0, data['line'])
        self.assertEqual({}, data['targets'])
        self.assertEqual("0", data['content-hash'])
        item.self_test()

    def test_add_invalid_attribute(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        self.assertFalse(item.get_attribute(self.attribute_key1))
        with self.assertRaises(exception.TraceabilityException):
            item.add_attribute(None, self.attribute_value1)
        with self.assertRaises(exception.TraceabilityException):
            item.add_attribute('', self.attribute_value1)
        with self.assertRaises(exception.TraceabilityException):
            item.add_attribute(self.attribute_key1, None)
        with self.assertRaises(exception.TraceabilityException):
            item.add_attribute(self.attribute_key1, '')
        with self.assertRaises(exception.TraceabilityException):
            item.add_attribute(self.attribute_key1, self.attribute_value_invalid)
        item.self_test()

    def test_add_attribute_overwrite(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        self.assertFalse(item.get_attribute(self.attribute_key1))
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        self.assertEqual(self.attribute_value1, item.get_attribute(self.attribute_key1))
        item.add_attribute(self.attribute_key1, self.attribute_value2)
        self.assertEqual(self.attribute_value2, item.get_attribute(self.attribute_key1))
        item.self_test()

    def test_add_attribute_no_overwrite(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        self.assertFalse(item.get_attribute(self.attribute_key1))
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        self.assertEqual(self.attribute_value1, item.get_attribute(self.attribute_key1))
        item.add_attribute(self.attribute_key1, self.attribute_value2, overwrite=False)
        self.assertEqual(self.attribute_value1, item.get_attribute(self.attribute_key1))
        item.self_test()

    def test_remove_invalid_attribute(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        self.assertFalse(item.get_attribute(self.attribute_key1))
        with self.assertRaises(exception.TraceabilityException):
            item.remove_attribute(None)
        with self.assertRaises(exception.TraceabilityException):
            item.remove_attribute('')
        item.self_test()

    def test_remove_attribute(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        self.assertEqual(self.attribute_value1, item.get_attribute(self.attribute_key1))
        item.remove_attribute(self.attribute_key1)
        self.assertFalse(item.get_attribute(self.attribute_key1))
        item.self_test()

    def test_get_attributes(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        self.assertEqual([''], item.get_attributes([self.attribute_key1]))
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        self.assertEqual([self.attribute_value1], item.get_attributes([self.attribute_key1]))
        item.add_attribute(self.attribute_key2, self.attribute_value2)
        self.assertEqual([self.attribute_value1], item.get_attributes([self.attribute_key1]))
        self.assertEqual([self.attribute_value2], item.get_attributes([self.attribute_key2]))
        self.assertEqual([self.attribute_value1, self.attribute_value2],
                         item.get_attributes([self.attribute_key1, self.attribute_key2]))
        self.assertEqual([self.attribute_value2, self.attribute_value1],
                         item.get_attributes([self.attribute_key2, self.attribute_key1]))
        item.self_test()

    def test_add_target_explicit_self(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        with self.assertRaises(exception.TraceabilityException):
            item.add_target(self.fwd_relation, self.identification, implicit=False)

    def test_add_target_implicit_self(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        with self.assertRaises(exception.TraceabilityException):
            item.add_target(self.fwd_relation, self.identification, implicit=True)

    def test_add_get_target_explicit(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        # Initially no targets (explicit+implicit)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(0, len(targets))
        relations = item.iter_relations()
        self.assertNotIn(self.fwd_relation, relations)
        # Add an explicit target
        item.add_target(self.fwd_relation, self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Add the same explicit target, should not change (no duplicates)
        with self.assertRaises(exception.TraceabilityException):
            item.add_target(self.fwd_relation, self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Add the same implicit target, should not change (is already explicit)
        with self.assertRaises(exception.TraceabilityException):
            item.add_target(self.fwd_relation, self.identification_tgt, implicit=True)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Verify relations iterator
        relations = item.iter_relations()
        self.assertIn(self.fwd_relation, relations)
        # Verify dict
        data = item.to_dict()
        self.assertEqual(self.identification, data['id'])
        self.assertEqual([self.identification_tgt], data['targets'][self.fwd_relation])
        self.assertEqual(self.docname, data['document'])
        self.assertEqual(0, data['line'])
        self.assertEqual("0", data['content-hash'])
        # Self test should pass
        item.self_test()

    def test_add_get_target_implicit(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        # Initially no targets (explicit+implicit)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(0, len(targets))
        relations = item.iter_relations()
        self.assertNotIn(self.fwd_relation, relations)
        # Add an implicit target
        item.add_target(self.fwd_relation, self.identification_tgt, implicit=True)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(0, len(targets))
        # Add the same implicit target, should not change (no duplicates)
        item.add_target(self.fwd_relation, self.identification_tgt, implicit=True)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(0, len(targets))
        # Add the same explicit target, should move the target to be explicit
        item.add_target(self.fwd_relation, self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation, explicit=False)
        self.assertEqual(0, len(targets))
        targets = item.iter_targets(self.fwd_relation, implicit=False)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Verify relations iterator
        relations = item.iter_relations()
        self.assertIn(self.fwd_relation, relations)
        # Verify dict
        data = item.to_dict()
        self.assertEqual(self.identification, data['id'])
        self.assertEqual([self.identification_tgt], data['targets'][self.fwd_relation])
        self.assertEqual(self.docname, data['document'])
        self.assertEqual(0, data['line'])
        self.assertEqual("0", data['content-hash'])
        # Self test should pass
        item.self_test()

    def test_remove_target_explicit(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        # Add an explicit target
        item.add_target(self.fwd_relation, self.identification_tgt)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Remove target to self and implicit targets, no effect
        item.remove_targets(self.identification)
        item.remove_targets(self.identification_tgt, explicit=False, implicit=True)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Remove explicit target to tgt, should be removed
        item.remove_targets(self.identification_tgt, explicit=True, implicit=False)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(0, len(targets))
        # Self test should pass
        item.self_test()

    def test_remove_target_implicit(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        # Add an implicit target
        item.add_target(self.fwd_relation, self.identification_tgt, implicit=True)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Remove target to self and explicit targets, no effect
        item.remove_targets(self.identification)
        item.remove_targets(self.identification_tgt, explicit=True, implicit=False)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(1, len(targets))
        self.assertEqual(targets[0], self.identification_tgt)
        # Remove implicit target to tgt, should be removed
        item.remove_targets(self.identification_tgt, explicit=False, implicit=True)
        targets = item.iter_targets(self.fwd_relation)
        self.assertEqual(0, len(targets))
        # Self test should pass
        item.self_test()

    def test_stringify(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        item.add_target(self.fwd_relation, self.identification_tgt, implicit=False)
        item.add_target(self.rev_relation, 'one more item', implicit=True)
        itemstr = str(item)
        self.assertIn(self.identification, itemstr)
        self.assertIn(self.attribute_key1, itemstr)
        self.assertIn(self.attribute_value1, itemstr)
        self.assertIn(self.fwd_relation, itemstr)
        self.assertIn(self.identification_tgt, itemstr)
        self.assertIn(self.rev_relation, itemstr)
        self.assertIn('one more item', itemstr)

    def test_match(self):
        item = dut.TraceableItem(self.identification)
        self.assertEqual(self.identification, item.identifier)
        self.assertFalse(item.is_match('some-name-that(will-definitely)not-match'))
        self.assertTrue(item.is_match('some'))
        self.assertTrue(item.is_match('some-random'))
        self.assertTrue(item.is_match(r'\w+'))
        self.assertTrue(item.is_match(r'[\w-]+andom'))

    def test_attributes_match(self):
        item = dut.TraceableItem(self.identification)
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        self.assertFalse(item.attributes_match({self.attribute_key1: self.attribute_value2}))
        self.assertTrue(item.attributes_match({self.attribute_key1: self.attribute_value1}))

    def test_related(self):
        item = dut.TraceableItem(self.identification)
        self.assertEqual(self.identification, item.identifier)
        self.assertFalse(item.is_related([self.fwd_relation], self.identification_tgt))
        item.add_target(self.fwd_relation, self.identification_tgt)
        self.assertTrue(item.is_related([self.fwd_relation], self.identification_tgt))
        self.assertFalse(item.is_related(['some-other-relation'], self.identification_tgt))

    def test_self_test_duplicate_relation(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        # Add a target
        item.add_target(self.fwd_relation, self.identification_tgt)
        # Self test should pass
        item.self_test()
        # Add same target (fails as it is not allowed)
        with self.assertRaises(exception.TraceabilityException):
            item.add_target(self.fwd_relation, self.identification_tgt)
        # Hack into class and add same relation anyway
        item.explicit_relations[self.fwd_relation].append(self.identification_tgt)
        # Self test should fail
        with self.assertRaises(exception.TraceabilityException):
            item.self_test()

    def test_self_test_invalid_attribute(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        # Add a valid attribute
        item.add_attribute(self.attribute_key1, self.attribute_value1)
        # Self test should pass
        item.self_test()
        # Add invalid attribute (fails as it is not allowed)
        with self.assertRaises(exception.TraceabilityException):
            item.add_attribute(self.attribute_key1, None)
        # Hack into class and add invalid attribute anyway
        item.attributes[self.attribute_key1] = None
        # Self test should fail
        with self.assertRaises(exception.TraceabilityException):
            item.self_test()

    def test_has_relations(self):
        item = dut.TraceableItem(self.identification)
        item.set_location(self.docname)
        item.add_target(self.fwd_relation, self.identification_tgt)
        self.assertEqual(item.has_relations([]), True)
        self.assertEqual(item.has_relations([self.fwd_relation]), True)
        self.assertEqual(item.has_relations([self.rev_relation]), False)
        self.assertEqual(item.has_relations([self.fwd_relation, self.rev_relation]), False)
        self.assertEqual(item.has_relations([self.rev_relation, self.fwd_relation]), False)
