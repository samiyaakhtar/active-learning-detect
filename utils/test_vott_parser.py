import unittest
import json
import pathlib
import os
from unittest.mock import Mock
from .vott_parser import process_vott_json, create_starting_vott_json, build_id_to_VottImageTag, create_vott_json_from_image_labels
from functions.pipeline.shared.db_access import ImageLabel

class TestVOTTParser(unittest.TestCase):
    def test_create_vott_json(self):
        dirname, _ = os.path.split(os.path.abspath(__file__))
        with open(dirname + '/mock_response.json') as f:
            data = json.load(f)
            image_labels = [ImageLabel.fromJson(item) for item in data]
            existing_classification_list = ['road', 'superdefect', 'test', 'water', 'superknot', 'knot', 'car', 'cloud', 'mountain', 'defect']
            vott_json, image_urls = create_vott_json_from_image_labels(image_labels, existing_classification_list)
            self.assertEqual(len(image_urls), 2)
            self.assertIsNotNone(vott_json["frames"]["199.JPG"])
            self.assertTrue("inputTags" in vott_json)


if __name__ == '__main__':
    unittest.main()


