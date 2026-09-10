#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFImage: Well Image Measurement

Wraps a PIL image loaded from a Crucible dataset download.

Created on Mon Jan 26 10:44:31 2026
@author: roncofaber
"""

import os
import logging

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import sobel
from scipy.signal import savgol_filter
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.feature import canny
from skimage.filters import gaussian
from skimage.measure import label, regionprops

# internal modules
from clabs.measurements.measurement import Measurement

# Set up logger for this module
logger = logging.getLogger(__name__)

#%%

class TFImage(Measurement):

    _mtype = "image"
    DEFAULT_ROI_FRACTION = 0.4

    def __init__(self, dataset, image_path):
        super().__init__(dataset)
        self.image = Image.open(image_path)
        self.image.load()  # force decode now so Pillow closes the file handle

    @property
    def sample_name(self):
        sm = self._dataset.scientific_metadata
        return sm.get("sample_name") if sm else None

    @property
    def sample_mfid(self):
        sm = self._dataset.scientific_metadata
        return sm.get("sample_mfid") if sm else None

    @classmethod
    def load(cls, dataset, files):
        """Open a well image from downloaded files. Returns a TFImage."""
        image_exts = {'.jpeg', '.jpg', '.png', '.gif', '.bmp',
                      '.tiff', '.tif', '.webp', '.heif', '.heic'}
        img_files = [f for f in files
                     if os.path.splitext(f)[1].lower() in image_exts]
        if not img_files:
            logger.warning(f"No image file found for dataset {dataset.name!r}")
            return None
        return cls(dataset, img_files[0])

    @staticmethod
    def _validate_roi_fraction(fraction):
        if not 0 < fraction <= 1:
            raise ValueError("ROI fraction must be greater than 0 and at most 1.")

    @staticmethod
    def _mad(values):
        values = np.asarray(values, dtype=float)
        return 1.4826 * np.median(np.abs(values - np.median(values)))

    @staticmethod
    def _smooth_profile(values):
        window = min(11, len(values) // 2 * 2 - 1)
        if window < 5:
            return values
        return savgol_filter(values, window_length=window, polyorder=2)

    def get_roi(self, fraction=DEFAULT_ROI_FRACTION):
        """Return a centered square crop as a PIL image."""
        self._validate_roi_fraction(fraction)
        width, height = self.image.size
        side = max(1, round(min(width, height) * fraction))
        left = (width - side) // 2
        top = (height - side) // 2
        return self.image.crop((left, top, left + side, top + side))

    def get_color_maps(self, fraction=DEFAULT_ROI_FRACTION):
        """Return RGB, CIELAB, chroma, hue, and CIEDE2000 maps for the ROI."""
        rgb = np.asarray(self.get_roi(fraction).convert("RGB"), dtype=float) / 255.0
        lab = rgb2lab(rgb)
        median_lab = np.median(lab.reshape(-1, 3), axis=0)
        reference = np.broadcast_to(median_lab, lab.shape)
        return {
            "rgb": rgb,
            "lab": lab,
            "l_star": lab[:, :, 0],
            "a_star": lab[:, :, 1],
            "b_star": lab[:, :, 2],
            "chroma": np.hypot(lab[:, :, 1], lab[:, :, 2]),
            "hue_radians": np.arctan2(lab[:, :, 2], lab[:, :, 1]),
            "delta_e_2000": deltaE_ciede2000(lab, reference),
            "median_lab": median_lab,
        }

    def get_histogram(
        self,
        channel="delta_e_2000",
        fraction=DEFAULT_ROI_FRACTION,
        bins=100,
        value_range=None,
        density=True,
        clip=False,
    ):
        """Return histogram values and bin edges for a visual channel."""
        maps = self.get_color_maps(fraction)
        if channel not in maps or np.asarray(maps[channel]).ndim != 2:
            valid = [
                key for key, value in maps.items() if np.asarray(value).ndim == 2
            ]
            raise ValueError(f"Unknown histogram channel {channel!r}. Choose from {valid}.")
        values = np.asarray(maps[channel], dtype=float).ravel()
        if value_range is None and channel == "hue_radians":
            value_range = (-np.pi, np.pi)
        if clip:
            if np.ndim(bins):
                lower, upper = np.asarray(bins, dtype=float)[[0, -1]]
            elif value_range is not None:
                lower, upper = value_range
            else:
                lower, upper = np.min(values), np.max(values)
            values = np.clip(values, lower, upper)
        return np.histogram(values, bins=bins, range=value_range, density=density)

    @staticmethod
    def _validate_grid(grid):
        if np.isscalar(grid):
            grid = (int(grid), int(grid))
        if len(grid) != 2 or any(int(value) < 2 for value in grid):
            raise ValueError("Grid must contain at least two rows and columns.")
        return tuple(int(value) for value in grid)

    @staticmethod
    def _hue_dispersion(hue, chroma):
        active = chroma > 1.0
        weights = chroma[active]
        if weights.sum() <= 1e-12:
            return np.nan
        cosine = np.sum(weights * np.cos(hue[active]))
        sine = np.sum(weights * np.sin(hue[active]))
        return 1.0 - np.hypot(cosine, sine) / weights.sum()

    def get_spatial_metrics(self, grid=(8, 8), fraction=DEFAULT_ROI_FRACTION):
        """Return grid-resolved perceptual color metrics for the ROI."""
        rows, columns = self._validate_grid(grid)
        maps = self.get_color_maps(fraction)
        lab = maps["lab"]
        row_edges = np.linspace(0, lab.shape[0], rows + 1, dtype=int)
        column_edges = np.linspace(0, lab.shape[1], columns + 1, dtype=int)
        values = {
            "median_l_star": [],
            "median_a_star": [],
            "median_b_star": [],
            "median_chroma": [],
            "delta_e_2000": [],
            "l_star_iqr": [],
            "chroma_mad": [],
            "hue_circular_dispersion": [],
        }
        for row in range(rows):
            for column in range(columns):
                block = lab[
                    row_edges[row] : row_edges[row + 1],
                    column_edges[column] : column_edges[column + 1],
                ]
                flat = block.reshape(-1, 3)
                median_lab = np.median(flat, axis=0)
                chroma = np.hypot(block[:, :, 1], block[:, :, 2])
                hue = np.arctan2(block[:, :, 2], block[:, :, 1])
                values["median_l_star"].append(median_lab[0])
                values["median_a_star"].append(median_lab[1])
                values["median_b_star"].append(median_lab[2])
                values["median_chroma"].append(np.median(chroma))
                values["delta_e_2000"].append(
                    deltaE_ciede2000(
                        median_lab[None, :], maps["median_lab"][None, :]
                    )[0]
                )
                values["l_star_iqr"].append(
                    np.subtract(*np.quantile(block[:, :, 0], [0.75, 0.25]))
                )
                values["chroma_mad"].append(self._mad(chroma))
                values["hue_circular_dispersion"].append(
                    self._hue_dispersion(hue, chroma)
                )
        result = {
            key: np.asarray(value).reshape(rows, columns)
            for key, value in values.items()
        }
        result["x_fraction"] = np.broadcast_to(
            (np.arange(columns) + 0.5) / columns, (rows, columns)
        )
        result["y_fraction"] = np.broadcast_to(
            ((np.arange(rows) + 0.5) / rows)[:, None], (rows, columns)
        )
        return result

    def get_morphology_maps(
        self,
        fraction=DEFAULT_ROI_FRACTION,
        background_sigma_fraction=0.03,
        anomaly_threshold_sigma=4.0,
        minimum_delta_e=1.0,
        minimum_component_fraction=0.0002,
        edge_sigma=1.5,
        edge_low_threshold=0.01,
        edge_high_threshold=0.03,
    ):
        """Return local color residual, anomaly, edge, and high-pass maps."""
        if background_sigma_fraction <= 0:
            raise ValueError("Background sigma fraction must be positive.")
        if anomaly_threshold_sigma <= 0:
            raise ValueError("Anomaly threshold sigma must be positive.")
        if minimum_delta_e < 0:
            raise ValueError("Minimum color difference must be non-negative.")
        if not 0 <= minimum_component_fraction < 1:
            raise ValueError("Minimum component fraction must be from 0 to 1.")
        if edge_sigma <= 0:
            raise ValueError("Edge sigma must be positive.")
        if not 0 <= edge_low_threshold < edge_high_threshold:
            raise ValueError("Edge thresholds must be ordered and non-negative.")

        maps = self.get_color_maps(fraction)
        lab = maps["lab"]
        sigma = max(1.0, min(lab.shape[:2]) * background_sigma_fraction)
        smooth_lab = gaussian(
            lab,
            sigma=sigma,
            preserve_range=True,
            channel_axis=-1,
        )
        local_delta_e = deltaE_ciede2000(lab, smooth_lab)
        center = np.median(local_delta_e)
        scale = self._mad(local_delta_e)
        threshold = max(
            minimum_delta_e,
            center + anomaly_threshold_sigma * scale,
        )
        anomaly_mask = local_delta_e > threshold
        component_labels = label(anomaly_mask, connectivity=2)
        minimum_area = max(
            1,
            round(anomaly_mask.size * minimum_component_fraction),
        )
        component_sizes = np.bincount(component_labels.ravel())
        keep = component_sizes >= minimum_area
        keep[0] = False
        anomaly_mask = keep[component_labels]
        component_labels = label(anomaly_mask, connectivity=2)

        normalized_lightness = maps["l_star"] / 100.0
        if np.ptp(normalized_lightness) > 1e-12:
            edge_map = canny(
                normalized_lightness,
                sigma=edge_sigma,
                low_threshold=edge_low_threshold,
                high_threshold=edge_high_threshold,
            )
        else:
            edge_map = np.zeros_like(normalized_lightness, dtype=bool)
        smooth_lightness = gaussian(
            normalized_lightness,
            sigma=sigma,
            preserve_range=True,
        )
        high_pass = normalized_lightness - smooth_lightness
        return {
            "lab": lab,
            "l_star": maps["l_star"],
            "local_delta_e_2000": local_delta_e,
            "local_delta_e_2000_threshold": threshold,
            "anomaly_mask": anomaly_mask,
            "component_labels": component_labels,
            "edge_map": edge_map,
            "high_pass_l_star": high_pass,
        }

    def get_anomaly_map(self, fraction=DEFAULT_ROI_FRACTION, **kwargs):
        """Return the robust local-color anomaly mask for the ROI."""
        return self.get_morphology_maps(fraction=fraction, **kwargs)["anomaly_mask"]

    def get_morphology_metrics(self, fraction=DEFAULT_ROI_FRACTION, **kwargs):
        """Calculate unsupervised morphology metrics within the ROI."""
        morphology_maps = self.get_morphology_maps(fraction=fraction, **kwargs)
        anomaly_mask = morphology_maps["anomaly_mask"]
        total_area = anomaly_mask.size
        regions = regionprops(morphology_maps["component_labels"])
        areas = np.asarray([region.area for region in regions], dtype=float)
        axis_ratios = []
        for region in regions:
            major = (
                region.axis_major_length
                if hasattr(region, "axis_major_length")
                else region.major_axis_length
            )
            minor = (
                region.axis_minor_length
                if hasattr(region, "axis_minor_length")
                else region.minor_axis_length
            )
            axis_ratios.append(major / max(minor, 1.0))
        axis_ratios = np.asarray(axis_ratios)
        compact = np.asarray(
            [region.eccentricity <= 0.8 and region.solidity >= 0.8 for region in regions]
        )

        lab = morphology_maps["lab"]
        height, width = lab.shape[:2]
        yy, xx = np.indices((height, width))
        radius = np.hypot(
            (xx - (width - 1) / 2) / (width / 2),
            (yy - (height - 1) / 2) / (height / 2),
        )
        inner = radius <= 1 / 3
        outer = (radius >= 2 / 3) & (radius <= 1)

        def median_color(mask):
            return np.median(lab[mask], axis=0)

        def color_difference(first, second):
            return deltaE_ciede2000(first[None, :], second[None, :])[0]

        left_right_delta_e = color_difference(
            median_color(xx < width / 3),
            median_color(xx >= 2 * width / 3),
        )
        top_bottom_delta_e = color_difference(
            median_color(yy < height / 3),
            median_color(yy >= 2 * height / 3),
        )
        radial_delta_e = color_difference(median_color(inner), median_color(outer))
        lightness_variance = np.var(morphology_maps["l_star"] / 100.0)
        high_pass_energy_ratio = (
            np.mean(morphology_maps["high_pass_l_star"] ** 2) / lightness_variance
            if lightness_variance > 1e-12
            else 0.0
        )

        return {
            "anomaly_threshold_delta_e_2000": morphology_maps[
                "local_delta_e_2000_threshold"
            ],
            "anomaly_fraction": np.mean(anomaly_mask),
            "anomaly_component_count": len(regions),
            "anomaly_component_density_per_megapixel": len(regions)
            / total_area
            * 1e6,
            "anomaly_largest_component_fraction": (
                np.max(areas) / total_area if len(areas) else 0.0
            ),
            "anomaly_median_component_fraction": (
                np.median(areas) / total_area if len(areas) else 0.0
            ),
            "elongated_anomaly_fraction": (
                np.sum(areas[axis_ratios >= 4.0]) / total_area
                if len(areas)
                else 0.0
            ),
            "compact_anomaly_fraction": (
                np.sum(areas[compact]) / total_area if len(areas) else 0.0
            ),
            "edge_density": np.mean(morphology_maps["edge_map"]),
            "high_pass_energy_ratio": high_pass_energy_ratio,
            "radial_delta_e_2000": radial_delta_e,
            "left_right_delta_e_2000": left_right_delta_e,
            "top_bottom_delta_e_2000": top_bottom_delta_e,
        }

    def plot_morphology(self, fraction=DEFAULT_ROI_FRACTION, **kwargs):
        """Plot the ROI and unsupervised morphology maps."""
        roi = self.get_roi(fraction)
        maps = self.get_morphology_maps(fraction=fraction, **kwargs)
        fig, axes = plt.subplots(1, 4, figsize=(14, 3.5))
        axes[0].imshow(roi)
        axes[0].set_title(f"Central {fraction:.0%} ROI")
        residual = axes[1].imshow(maps["local_delta_e_2000"], cmap="magma")
        axes[1].set_title("Local CIEDE2000 residual")
        fig.colorbar(residual, ax=axes[1], label="Color difference")
        axes[2].imshow(maps["anomaly_mask"], cmap="gray")
        axes[2].set_title("Color anomaly mask")
        axes[3].imshow(maps["edge_map"], cmap="gray")
        axes[3].set_title("Canny edge map")
        for axis in axes:
            axis.axis("off")
        fig.tight_layout()
        return fig, axes

    def get_inhomogeneity(
        self,
        fraction=DEFAULT_ROI_FRACTION,
        spatial_blocks=8,
        aspect_range=(0.95, 1.05),
        boundary_threshold=8.0,
    ):
        """Calculate robust perceptual color, hue, spatial, and QC metrics."""
        if spatial_blocks < 2:
            raise ValueError("At least two spatial blocks are required.")
        maps = self.get_color_maps(fraction)
        lab = maps["lab"]
        flat_lab = lab.reshape(-1, 3)
        l_star = maps["l_star"]
        a_star = maps["a_star"]
        b_star = maps["b_star"]
        chroma = maps["chroma"]
        hue = maps["hue_radians"]
        delta_e = maps["delta_e_2000"]

        active_hue = chroma > 1.0
        hue_weights = chroma[active_hue]
        if hue_weights.sum() > 1e-12:
            cosine = np.sum(hue_weights * np.cos(hue[active_hue]))
            sine = np.sum(hue_weights * np.sin(hue[active_hue]))
            hue_dispersion = 1.0 - np.hypot(cosine, sine) / hue_weights.sum()
        else:
            hue_dispersion = np.nan

        row_edges = np.linspace(0, lab.shape[0], spatial_blocks + 1, dtype=int)
        column_edges = np.linspace(0, lab.shape[1], spatial_blocks + 1, dtype=int)
        block_colors = []
        for row in range(spatial_blocks):
            for column in range(spatial_blocks):
                block = lab[
                    row_edges[row] : row_edges[row + 1],
                    column_edges[column] : column_edges[column + 1],
                ]
                if block.size:
                    block_colors.append(np.median(block.reshape(-1, 3), axis=0))
        block_colors = np.asarray(block_colors)
        block_reference = np.broadcast_to(maps["median_lab"], block_colors.shape)
        block_delta_e = deltaE_ciede2000(block_colors, block_reference)

        normalized_lightness = l_star / 100.0
        gradient = np.hypot(
            sobel(normalized_lightness, axis=0),
            sobel(normalized_lightness, axis=1),
        )
        row_profile = self._smooth_profile(np.median(l_star, axis=1))
        column_profile = self._smooth_profile(np.median(l_star, axis=0))
        axis_boundary_jump = max(
            np.max(np.abs(np.diff(row_profile))),
            np.max(np.abs(np.diff(column_profile))),
        )

        histogram, _ = np.histogram(delta_e, bins=64)
        probabilities = histogram / histogram.sum()
        probabilities = probabilities[probabilities > 0]
        histogram_entropy = -np.sum(probabilities * np.log(probabilities))
        width, height = self.image.size
        aspect_ratio = width / height
        aspect_valid = aspect_range[0] <= aspect_ratio <= aspect_range[1]
        center_boundary_valid = axis_boundary_jump <= boundary_threshold

        return {
            "roi_fraction": fraction,
            "image_width": width,
            "image_height": height,
            "image_aspect_ratio": aspect_ratio,
            "central_crop_side_px": lab.shape[0],
            "median_l_star": np.median(flat_lab[:, 0]),
            "median_a_star": np.median(flat_lab[:, 1]),
            "median_b_star": np.median(flat_lab[:, 2]),
            "median_chroma": np.median(chroma),
            "l_star_iqr": np.subtract(*np.quantile(l_star, [0.75, 0.25])),
            "l_star_mad": self._mad(l_star),
            "a_star_mad": self._mad(a_star),
            "b_star_mad": self._mad(b_star),
            "chroma_mad": self._mad(chroma),
            "hue_circular_dispersion": hue_dispersion,
            "delta_e_2000_median": np.median(delta_e),
            "delta_e_2000_mad": self._mad(delta_e),
            "delta_e_2000_p90": np.quantile(delta_e, 0.90),
            "delta_e_2000_p95": np.quantile(delta_e, 0.95),
            "spatial_delta_e_2000_median": np.median(block_delta_e),
            "spatial_delta_e_2000_p90": np.quantile(block_delta_e, 0.90),
            "l_star_gradient_median": np.median(gradient),
            "delta_e_histogram_entropy": histogram_entropy,
            "saturation_fraction": np.mean(
                np.any((maps["rgb"] <= 0.005) | (maps["rgb"] >= 0.995), axis=2)
            ),
            "axis_boundary_jump_l_star": axis_boundary_jump,
            "aspect_valid": aspect_valid,
            "center_boundary_valid": center_boundary_valid,
            "qc_valid": aspect_valid and center_boundary_valid,
        }

    def plot_inhomogeneity(self, fraction=DEFAULT_ROI_FRACTION, bins=60):
        """Plot the ROI, CIEDE2000 map, and pixel color-difference histogram."""
        roi = self.get_roi(fraction)
        maps = self.get_color_maps(fraction)
        histogram, edges = self.get_histogram(
            channel="delta_e_2000",
            fraction=fraction,
            bins=bins,
            density=True,
        )
        centers = (edges[:-1] + edges[1:]) / 2
        fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
        axes[0].imshow(roi)
        axes[0].set_title(f"Central {fraction:.0%} ROI")
        axes[0].axis("off")
        color_map = axes[1].imshow(maps["delta_e_2000"], cmap="magma")
        axes[1].set_title("CIEDE2000 from median color")
        axes[1].axis("off")
        fig.colorbar(color_map, ax=axes[1], label="Color difference")
        axes[2].plot(centers, histogram, color="#333333")
        axes[2].set_xlabel("CIEDE2000 from median color")
        axes[2].set_ylabel("Probability density")
        axes[2].grid(alpha=0.2)
        fig.tight_layout()
        return fig, axes

    def view(self, console=False):
        """Display the image associated with the instance."""
        if self.image is not None:
            plt.figure(figsize=(3, 3))
            plt.imshow(self.image, cmap='gray')
            plt.axis('off')
            plt.show(block=not console)
        else:
            logger.info("No image to display")
