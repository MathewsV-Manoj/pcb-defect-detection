import unittest

from pcb_engine_kit.compare_pt_onnx import box_iou, match_detections


class OnnxParityContractTests(unittest.TestCase):
    def test_identical_boxes_have_unit_iou(self):
        self.assertAlmostEqual(box_iou([10, 10, 20, 20], [10, 10, 20, 20]), 1.0)

    def test_disjoint_boxes_have_zero_iou(self):
        self.assertAlmostEqual(box_iou([0, 0, 10, 10], [20, 20, 30, 30]), 0.0)

    def test_same_class_boxes_match_one_to_one(self):
        reference = [
            {"class_id": 1, "confidence": 0.80, "xyxy": [10, 10, 20, 20]},
            {"class_id": 2, "confidence": 0.73, "xyxy": [30, 30, 40, 40]},
        ]
        candidate = [
            {"class_id": 1, "confidence": 0.81, "xyxy": [10, 10, 20, 20]},
            {"class_id": 2, "confidence": 0.72, "xyxy": [30, 30, 40, 40]},
        ]
        result = match_detections(reference, candidate, 0.98)
        self.assertEqual(result["matched_count"], 2)
        self.assertEqual(result["unmatched_reference_count"], 0)
        self.assertEqual(result["unmatched_candidate_count"], 0)

    def test_different_class_ids_do_not_match_even_when_boxes_overlap(self):
        reference = [{"class_id": 1, "confidence": 0.80, "xyxy": [10, 10, 20, 20]}]
        candidate = [{"class_id": 2, "confidence": 0.80, "xyxy": [10, 10, 20, 20]}]
        result = match_detections(reference, candidate, 0.98)
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["unmatched_reference_count"], 1)
        self.assertEqual(result["unmatched_candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
