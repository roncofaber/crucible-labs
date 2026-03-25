#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  5 13:09:34 2026

@author: roncofaber
"""

# internal modules
from clabs import Sample, Dataset
from clabs.collection import SampleCollection, DatasetCollection
from clabs.graph.graph import build_project_graph
from clabs.models import ProjectModel
from crucible.config import get_client, get_cache_dir

# Set up logger for this module
import logging
logger = logging.getLogger(__name__)

# graph operations
import networkx as nx

#%%

class CrucibleProject:

    def __init__(self, project_id, cache_dir=None, use_cache=True,
                 overwrite_cache=False):

        # store cache settings
        self._cache_dir       = cache_dir if cache_dir is not None else str(get_cache_dir())
        self._use_cache       = use_cache
        self._overwrite_cache = overwrite_cache

        # fetch and validate project metadata
        project_dict = self.client.projects.get(project_id)
        if project_dict is None:
            raise ValueError(f"Project '{project_id}' not found. Check the project ID or your permissions.")
        self._project    = ProjectModel.model_validate(project_dict)
        self._project_id = self._project.project_id

        # 1. load and instantiate datasets
        self._datasets = self._load_datasets(project_id)

        # 2. load and instantiate samples
        self._samples = self._load_samples(project_id)

        # 3. build centralized type-agnostic resource map
        self._build_resource_map()

        # 5. link all relationships from the entity graph
        self._setup_graph()

    #%% client

    @property
    def client(self):
        return get_client()

    @property
    def project_id(self):
        return self._project_id

    #%% collections (top-level)

    @property
    def samples(self):
        return self._samples

    @property
    def datasets(self):
        return self._datasets

    @property
    def graph(self):
        return self._graph

    #%% delegation to SampleCollection

    def __iter__(self):
        return iter(self._samples)

    def __len__(self):
        return len(self._samples)

    def __getitem__(self, index):
        return self._samples[index]

    def __contains__(self, sample):
        return sample in self._samples

    def get_sample(self, sample_id=None, sample_name=None):
        return self._samples.get_sample(sample_id=sample_id, sample_name=sample_name)

    #%% delegation to DatasetCollection

    def get_dataset(self, dataset_id=None, dataset_name=None):
        return self._datasets.get_dataset(dataset_id=dataset_id, dataset_name=dataset_name)

    #%% loading

    def _load_datasets(self, project_id):
        """Fetch datasets from API, create Dataset objects, return DatasetCollection."""
        raw = self.client.datasets.list(
            project_id       = project_id,
            include_metadata = True,
            limit            = int(1e8),
        )

        datasets = []
        for dst in raw:
            try:
                datasets.append(Dataset(dst))
            except Exception as e:
                logger.error(f"Failed to create Dataset {dst.get('unique_id')}: {e}")

        return DatasetCollection(datasets=datasets, project_id=project_id)

    def _load_samples(self, project_id):
        """Fetch samples from API, create Sample objects, return SampleCollection."""
        raw = self.client.samples.list(
            project_id  = project_id,
            sample_type = None,
            limit       = 1e8,
        )
        raw = sorted(raw, key=lambda x: x["sample_name"])

        samples = []
        for dst in raw:
            try:
                samples.append(Sample(dst))
            except Exception as e:
                logger.error(f"Failed to create Sample '{dst.get('sample_name')}': {e}")

        return SampleCollection(samples=samples, project_id=project_id)

    def _build_resource_map(self):
        """Centralized type-agnostic map: unique_id → Sample or Dataset."""
        self._resources = {
            **self._samples._samples_by_id,
            **self._datasets._datasets_by_id,
        }

    def get_resource(self, resource_id):
        """Get any resource (Sample or Dataset) by unique_id."""
        return self._resources.get(resource_id)

    def _get_project_graph(self):
        return self.client._request("get", f"/projects/{self.project_id}/sample_graph")

    def _get_dataset_graph(self):
        return self.client._request("get", f"/projects/{self.project_id}/dataset_graph")

    def _get_entity_graph(self):
        return self.client._request("get", f"/projects/{self.project_id}/entity_graph")

    def _setup_graph(self):
        graph = self._get_entity_graph()

        # networkx node-link format uses "links"; flat API format uses "edges"
        edges = graph.get("edges") or graph.get("links", [])

        for edge in edges:
            parent = self.get_resource(edge["source"])
            child  = self.get_resource(edge["target"])

            if parent is None or child is None:
                logger.warning(
                    f"Graph edge {edge['source']} → {edge['target']} references unknown resource, skipping"
                )
                continue

            if parent.kind == child.kind:
                # same-type: sample→sample or dataset→dataset genealogy
                child.add_parent(parent)
            else:
                # cross-type: sample↔dataset association (add_dataset handles both sides)
                sample  = parent if parent.kind == "sample" else child
                dataset = parent if parent.kind == "dataset" else child
                sample.add_dataset(dataset)

        # unified graph: all samples and datasets as nodes
        self._graph = build_project_graph(self._resources.values())

    #%% measurement loading

    def _get_measurement_data(self, measurement_type, description, sample_type=None):
        """
        Download and parse all datasets of a given measurement type.

        Dispatches via the loader registered with Dataset.register_loader().
        Sample matching is handled inside dataset.load().

        Parameters
        ----------
        measurement_type : str
            The mtype string to filter datasets on.
        description : str
            Label for the progress bar.
        sample_type : str, optional
            If given, only process datasets belonging to samples of this type.
        """
        from tqdm import tqdm
        from tqdm.contrib.logging import logging_redirect_tqdm
        from concurrent.futures import ThreadPoolExecutor, as_completed

        collection = self._samples.filter(sample_type=sample_type) if sample_type else self._samples
        datasets   = collection.samples_datasets.filter(measurement=measurement_type)
        cache_dir  = self._cache_dir + "/datasets"
        n          = len(datasets)

        tqdm.write(f"\n  {measurement_type}  ({n} datasets)")
        tqdm.write("  " + "─" * 52)

        bar_kwargs = dict(unit="dts", leave=True, ncols=72)

        with logging_redirect_tqdm():

            # phase 1: prefetch all files in parallel (pure I/O, no shared state)
            def _prefetch(dataset):
                dataset.prefetch(self.client, cache_dir, overwrite_existing=self._overwrite_cache)

            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(_prefetch, ds): ds for ds in datasets}
                for future in tqdm(as_completed(futures), total=n,
                                   desc="  downloading", **bar_kwargs):
                    future.result()  # surface any download exceptions

            # phase 2: parse sequentially (modifies shared sample state)
            for dataset in tqdm(datasets, desc="  parsing    ", **bar_kwargs):
                try:
                    dataset.load(
                        self.client,
                        cache_dir          = cache_dir,
                        use_cache          = self._use_cache,
                        overwrite_existing = self._overwrite_cache,
                    )
                except NotImplementedError:
                    logger.warning(f"No loader for {dataset.dtype!r}, skipping {dataset.name!r}")

    def load_measurements(self, measurement_type, sample_type=None):
        """
        Download and parse all datasets of a given measurement type.

        Parameters
        ----------
        measurement_type : str
            The mtype string to filter datasets on (e.g. 'pollux_oospec_multipos_line_scan').
        sample_type : str, optional
            If given, only process datasets belonging to samples of this type.
        """
        from clabs.measurements import register_loaders
        register_loaders()  # ensures all built-in loaders are registered
        self._get_measurement_data(
            measurement_type = measurement_type,
            description      = measurement_type,
            sample_type      = sample_type,
        )

    #%% graph genealogy helpers

    def _resolve_sample(self, sample):
        """Resolve a string name/id to a Sample object, or return as-is."""
        if isinstance(sample, str):
            result = self.get_sample(sample_id=sample, sample_name=sample)
            if result is None:
                logger.warning(f"Sample '{sample}' not found")
            return result
        return sample

    def get_ancestors(self, sample):
        """Get all ancestor samples using the project graph."""
        sample = self._resolve_sample(sample)
        if sample is None or sample not in self._graph:
            return []
        return list(nx.ancestors(self._graph, sample))

    def get_descendants(self, sample):
        """Get all descendant samples using the project graph."""
        sample = self._resolve_sample(sample)
        if sample is None or sample not in self._graph:
            return []
        return list(nx.descendants(self._graph, sample))

    def get_common_ancestors(self, sample1, sample2):
        """Find common ancestors of two samples."""
        sample1 = self._resolve_sample(sample1)
        sample2 = self._resolve_sample(sample2)
        if sample1 is None or sample2 is None:
            return []
        if sample1 not in self._graph or sample2 not in self._graph:
            return []
        return list(nx.ancestors(self._graph, sample1) & nx.ancestors(self._graph, sample2))

    def get_siblings(self, sample):
        """Get sibling samples (samples sharing at least one parent)."""
        sample = self._resolve_sample(sample)
        if sample is None or sample not in self._graph:
            return []
        parents  = list(self._graph.predecessors(sample))
        siblings = set()
        for parent in parents:
            siblings.update(self._graph.successors(parent))
        siblings.discard(sample)
        return list(siblings)

    def get_samples_with_ancestor(self, ancestor):
        """Get all samples descended from the given ancestor."""
        return self.get_descendants(ancestor)

    #%% project metadata

    @property
    def title(self):
        return self._project.title

    @property
    def organization(self):
        return self._project.organization

    @property
    def project_lead(self):
        return self._project.project_lead_name

    @property
    def status(self):
        return self._project.status

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(\n"
            f"  project_id={self._project.project_id!r},\n"
            f"  title={self.title!r},\n"
            f"  organization={self.organization!r},\n"
            f"  status={self.status!r}\n"
            f")"
        )

    def __getattr__(self, name):
        if name == "_project":
            raise AttributeError("_project not initialized")
        try:
            return getattr(self._project, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
