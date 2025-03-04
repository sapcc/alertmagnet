import unittest


from filtering.data_filter import create_time_ranges, remove_state_from_timestamp_value


class TestFilter(unittest.TestCase):
    def test_remove_state_from_timestamp_value_with_normal_input(self):
        data = [[0.0, "1"], [13.0, "1"]]

        expected_result = [0.0, 13]
        result = remove_state_from_timestamp_value(data=data)

        self.assertEqual(result, expected_result)

    def test_remove_state_from_timestamp_value_with_empty_input(self):
        data = []

        expected_result = []
        result = remove_state_from_timestamp_value(data=data)

        self.assertEqual(result, expected_result)

    def test_remove_state_from_timestamp_value_with_wrong_inputs_1(self):
        data = "ABAP"

        with self.assertRaises(TypeError):
            remove_state_from_timestamp_value(data=data)

    def test_remove_state_from_timestamp_value_with_wrong_inputs_2(self):
        data = ["ABAP"]

        with self.assertRaises(TypeError):
            remove_state_from_timestamp_value(data=data)

    def test_remove_state_from_timestamp_value_with_wrong_inputs_3(self):
        data = [["ABAP"]]

        with self.assertRaises(TypeError):
            remove_state_from_timestamp_value(data=data)

    def test_create_time_ranges_with_normal_input(self):
        data = [0, 5, 10, 15, 35, 50, 55, 60, 65, 67, 68, 69, 73, 78, 83, 88, 90]
        step = 5

        expected_result = [(0, 15), (35, 0), (50, 15), (67, 0), (68, 0), (69, 0), (73, 15), (90, 0)]

        result = create_time_ranges(data=data, step=step)

        self.assertEqual(result, expected_result)

    def test_create_time_ranges_with_empty_input(self):
        data = []
        step = 5

        expected_result = []

        result = create_time_ranges(data=data, step=step)

        self.assertEqual(result, expected_result)

    def test_create_time_ranges_with_continous_input(self):
        data = [0, 5, 10, 15, 20, 25]
        step = 5

        expected_result = [(0, 25)]

        result = create_time_ranges(data=data, step=step)

        self.assertEqual(result, expected_result)

    def test_create_time_ranges_with_continous_double_input(self):
        data = [0, 5, 10, 15, 20, 20, 25]
        step = 5

        expected_result = [(0, 25)]

        result = create_time_ranges(data=data, step=step)

        self.assertEqual(result, expected_result)

    def test_create_time_ranges_with_one_input(self):
        data = [77]
        step = 5

        expected_result = [(77, 0)]

        result = create_time_ranges(data=data, step=step)

        self.assertEqual(result, expected_result)

    def test_create_time_ranges_with_wrong_input(self):
        data = "ABAP"
        step = 5

        with self.assertRaises(TypeError):
            create_time_ranges(data=data, step=step)


if __name__ == "__main__":
    unittest.main()
