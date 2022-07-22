from collections import namedtuple
from unittest import TestCase

from docutils import nodes
from mlx.directives.item_matrix_directive import ItemMatrix

from parameterized import parameterized


class TestItemMatrix(TestCase):
    Rows = namedtuple('Rows', "sorted covered uncovered counters")

    @parameterized.expand([
        (True, True, [0, 0], [1, 1, 0]),
        (False, True, [0, 0], [1, 0, 1]),
    ])
    def test_store_data(self, covered, splittargets, attributes, expected_lengths):
        dut = ItemMatrix()
        dut['intermediate'] = ''
        dut['sourcecolumns'] = ['attr'] * attributes[0]
        dut['targetcolumns'] = ['attr'] * attributes[1]
        dut['splittargets'] = splittargets
        rows = self.Rows([], [], [], [0, 0])
        left = nodes.entry('left')
        target1 = [nodes.entry('right1')]
        target2 = [nodes.entry('right2')]
        dut._store_data(rows, left, [target1, target2], covered, None)

        self.assertEqual([len(attr) for attr in rows[:3]], expected_lengths)
        my_row = nodes.row()
        my_row += left
        my_row += target1
        my_row += target2
        for idx, rows_per_type in enumerate(rows[:3]):  # verify that rows contain the three entries
            self.assertEqual(str(rows_per_type), str([my_row] * expected_lengths[idx]))
