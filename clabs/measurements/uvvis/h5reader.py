#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H5 Reader: HDF5 Data Reader and Parser for UV-Vis

Converts HDF5 files from Nirvana UV-Vis measurements into NirvanaUVVis objects
with support for both new and legacy file formats, automatic carrier attribute
extraction, and energy range filtering.

Created on Mon Dec 22 15:24:53 2025
@author: roncofaber
"""

# pn
import numpy as np

# internal modules
from clabs.measurements.uvvis.uvvis import NirvanaUVVis
from clabs.utils.auxiliary import number_to_well

# echfive
import h5py

#%%

def h5_to_samples(dataset, h5filename, erange=None):
    try:
        samples = h5_to_samples_new(dataset, h5filename, erange=erange)
    except:
        try:
            samples = h5_to_samples_old(dataset, h5filename, erange=erange)
        except:
            raise ValueError
    return samples


def attrs2uvvis(dataset, sample_attrs, tray_well, wavelengths, raw_intensities,
                blank_intensities, dark_intensities, erange, measurement_settings,
                carrier_attrs):

    # make it an object
    uvvis_sample = NirvanaUVVis(
        dataset=dataset,
        sample_attrs=sample_attrs,
        tray_well=tray_well,
        wavelengths=wavelengths,
        raw_intensities=raw_intensities,
        blank_intensities=blank_intensities,
        dark_intensities=dark_intensities,
        erange=erange,
        measurement_settings=measurement_settings,
        carrier_attrs=carrier_attrs
        )

    return uvvis_sample

def h5_to_samples_new(dataset, h5filename, erange=None):


    with h5py.File(h5filename, 'r') as h5file:

        # get carrier information
        carrier_attrs = dict(h5file.attrs)

        # get wavelengths (same for all measurments)
        try:
            wavelengths = h5file['measurement/pollux_oospec_multipos_line_scan/wavelengths'][()]
        except:
            wavelengths = h5file['wavelengths'][()]

        # get measurements settings
        try:
            measurement_settings = dict(h5file['measurement/pollux_oospec_multipos_line_scan/settings'].attrs)
        except:
            measurement_settings = dict(h5file['settings'].attrs)

        # isolate relevant H5 group and get list of positions
        h5group   = h5file['measurement/pollux_oospec_multipos_line_scan/positions']

        # read each position and return NirvanaUVVis object
        samples_list = []
        for poskey in h5group:

            # get sample attributes
            sample_attrs = dict(h5group[poskey].attrs)

            # get raw intensities
            raw_intensities = h5group[poskey]['raw_intensities'][()]

            # get blank intensities
            blank_intensities = h5group[poskey]['blank_intensities'][()]

            # get dark intensities
            dark_intensities = h5group[poskey]['dark_intensities'][()]

            tray_well = number_to_well(int(poskey.split("_")[1]))

            uvvis_sample = attrs2uvvis(dataset, sample_attrs, tray_well,
                                       wavelengths, raw_intensities,
                                       blank_intensities, dark_intensities,
                                       erange, measurement_settings, carrier_attrs)

            samples_list.append(uvvis_sample)

    return samples_list

def h5_to_samples_old(dataset, h5filename, erange=None):
    with h5py.File(h5filename, 'r') as h5file:

        # get carrier information
        carrier_attrs = dict(h5file.attrs)

        # get wavelengths (same for all measurments)
        wavelengths = h5file['measurement/pollux_oospec_multipos_line_scan/wavelengths'][()]

        # get measurements settings
        measurement_settings = dict(h5file['measurement/pollux_oospec_multipos_line_scan/settings'].attrs)

        # isolate relevant H5 group and get list of positions
        h5group   = h5file['measurement/pollux_oospec_multipos_line_scan/positions']

        # read each position and return NirvanaUVVis object
        samples_list = []
        for poskey in h5group:

            if "Dark" in poskey:
                dark_intensities = h5group[poskey]['spectral_data'][()]
                continue
            if "Blank" in poskey:
                blank_intensities = h5group[poskey]['spectral_data'][()]
                continue

            # get sample attributes
            sample_attrs = dict(h5group[poskey].attrs)

            # fix some attributes
            sample_attrs["x_center"] = h5group[poskey]['x_center'][()]
            sample_attrs["y_center"] = h5group[poskey]['y_center'][()]
            sample_attrs["y_positions"] = h5group[poskey]['y_positions'][()]
            try:
                sample_attrs["x_positions"] = h5group[poskey]['x_positions'][()]
            except:
                sample_attrs["x_positions"] = np.array(
                    [h5group[poskey]['x_center'][()]]*len(sample_attrs["y_positions"]))

            # get raw intensities
            try:
                raw_intensities = h5group[poskey]['raw_intensities'][()]
            except:
                raw_intensities = h5group[poskey]['spectral_data'][()]

            # complete sample attributes
            tray_well = number_to_well(int(poskey.split("_")[1])-2)

            if "sample_name" not in sample_attrs:
                sample_attrs["sample_name"] = "TF" + poskey.split("_")[2][2:].zfill(6)
            if "sample_uuid" not in sample_attrs:
                sample_attrs["sample_uuid"] = None
            if "integration_time" not in sample_attrs:
                sample_attrs["integration_time"] = float(measurement_settings["spec_integration_time"])

            # make it an object
            uvvis_sample = attrs2uvvis(dataset, sample_attrs, tray_well,
                                       wavelengths, raw_intensities,
                                       blank_intensities, dark_intensities,
                                       erange, measurement_settings, carrier_attrs)

            samples_list.append(uvvis_sample)

    return samples_list
