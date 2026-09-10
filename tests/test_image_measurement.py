import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from clabs.measurements.image import TFImage


class TFImageAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "image.png"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def measurement(self, array):
        Image.fromarray(array.astype(np.uint8)).save(self.path)
        return TFImage(dataset=None, image_path=self.path)

    def test_default_roi_is_centered_forty_percent_square(self):
        array = np.full((80, 100, 3), 128)
        image = self.measurement(array)
        self.assertEqual(image.get_roi().size, (32, 32))

    def test_uniform_image_has_zero_color_spread(self):
        array = np.full((100, 100, 3), [120, 80, 40])
        metrics = self.measurement(array).get_inhomogeneity()
        self.assertAlmostEqual(metrics["delta_e_2000_median"], 0.0)
        self.assertAlmostEqual(metrics["spatial_delta_e_2000_median"], 0.0)
        self.assertTrue(metrics["qc_valid"])

    def test_color_split_has_positive_color_and_spatial_spread(self):
        array = np.full((100, 100, 3), [120, 80, 40])
        array[:, 50:] = [40, 100, 160]
        metrics = self.measurement(array).get_inhomogeneity()
        self.assertGreater(metrics["delta_e_2000_median"], 0.0)
        self.assertGreater(metrics["spatial_delta_e_2000_median"], 0.0)

    def test_histogram_and_plot_are_available(self):
        array = np.full((80, 100, 3), [120, 80, 40])
        image = self.measurement(array)
        histogram, edges = image.get_histogram(bins=12)
        self.assertEqual(len(histogram), 12)
        self.assertEqual(len(edges), 13)
        figure, axes = image.plot_inhomogeneity()
        self.assertEqual(len(axes), 3)
        plt.close(figure)

    def test_invalid_roi_fraction_is_rejected(self):
        array = np.full((80, 100, 3), 128)
        image = self.measurement(array)
        with self.assertRaises(ValueError):
            image.get_roi(1.1)

    def test_spatial_metrics_preserve_grid_shape(self):
        array = np.full((100, 120, 3), [120, 80, 40])
        array[:, 60:] = [40, 100, 160]
        metrics = self.measurement(array).get_spatial_metrics(grid=(4, 5))
        self.assertEqual(metrics["delta_e_2000"].shape, (4, 5))
        self.assertEqual(metrics["x_fraction"].shape, (4, 5))
        self.assertGreater(np.ptp(metrics["median_a_star"]), 0.0)

    def test_local_color_anomaly_is_detected(self):
        array = np.full((100, 100, 3), [120, 80, 40])
        array[45:55, 45:55] = [20, 140, 180]
        image = self.measurement(array)
        anomaly = image.get_anomaly_map()
        metrics = image.get_morphology_metrics()
        self.assertEqual(anomaly.shape, (40, 40))
        self.assertGreater(np.mean(anomaly), 0.0)
        self.assertGreater(metrics["anomaly_component_count"], 0)
        self.assertGreater(metrics["anomaly_fraction"], 0.0)

    def test_uniform_image_has_zero_morphology_signal(self):
        array = np.full((100, 100, 3), [120, 80, 40])
        metrics = self.measurement(array).get_morphology_metrics()
        self.assertEqual(metrics["anomaly_component_count"], 0)
        self.assertAlmostEqual(metrics["anomaly_fraction"], 0.0)
        self.assertAlmostEqual(metrics["edge_density"], 0.0)
        self.assertAlmostEqual(metrics["radial_delta_e_2000"], 0.0)

    def test_morphology_plot_is_available(self):
        array = np.full((80, 100, 3), [120, 80, 40])
        figure, axes = self.measurement(array).plot_morphology()
        self.assertEqual(len(axes), 4)
        plt.close(figure)

    def test_invalid_morphology_parameters_are_rejected(self):
        array = np.full((80, 100, 3), 128)
        image = self.measurement(array)
        with self.assertRaises(ValueError):
            image.get_spatial_metrics(grid=(1, 4))
        with self.assertRaises(ValueError):
            image.get_morphology_maps(background_sigma_fraction=0)


if __name__ == "__main__":
    unittest.main()
