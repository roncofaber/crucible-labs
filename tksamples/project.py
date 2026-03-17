#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  5 13:09:34 2026

@author: roncofaber
"""

# internal modules
from tksamples import Sample
from tksamples.collection import SampleCollection
from tksamples.graph.graph import build_project_graph
from tksamples.crucible.config import get_cache_dir

# avoid circular import by importing inside method
# from tksamples import Samples

# Set up logger for this module
import logging
logger = logging.getLogger(__name__)

# graph operations
import networkx as nx

#%%

class CrucibleProject(SampleCollection):

    def __init__(self, project_id, cache_dir=None, use_cache=True,
                 overwrite_cache=False):

        # store cache settings
        self._cache_dir = cache_dir if cache_dir is not None else str(get_cache_dir())
        self._use_cache = use_cache
        self._overwrite_cache = overwrite_cache

        # load datasets and samples
        self._datasets = self._load_datasets(project_id)
        self._samples = self._load_samples(project_id)
        
        self._assign_datasets_to_samples()
        
        # initialize parent class to enable list operations
        super().__init__(samples=self._samples, project_id=project_id)

        # build project graph
        self._setup_graph()

        return
    
    def _load_samples(self, project_id):
        """Load all samples from the Crucible project."""
        
        # get all samples and datasets
        dsts_samples = self.client.samples.list(
            project_id=project_id, sample_type=None, limit=1e8)
        dsts_samples = sorted(dsts_samples, key=lambda x: x["sample_name"])
        
        return dsts_samples

    def _load_datasets(self, project_id):
        
        self._datasets = self.client.datasets.list(
            project_id       = project_id,
            include_metadata = True,
            limit            = 1e8,
            )

        # create mapping of datasets with metadata
        self._datasets_by_id = {dst["unique_id"]:dst for dst in self._datasets}
        
        return
    
    def _assign_datasets_to_samples(self):
        
        # create one sample obj for each sample dataset
        samples = []
        for dst_sample in self._samples:

            for dst in dst_sample.get("datasets", []):
                try:
                    dst.update(self._datasets_by_id[dst["unique_id"]])
                except:
                    print(dst)

            try:
                tf = Sample(dst_sample)
                samples.append(tf)
            except Exception as e:
                logger.error(f"Failed to create Sample from dataset: {e}")
                logger.error(f"Dataset details:\n\t{dst_sample}")
        
        self._samples = samples
        return

    def _get_project_graph(self):
        return self.client._request("GET",f"/projects/{self.project_id}/sample_graph")
    
    def _setup_mapping(self):
        """Extend parent mapping with sample type grouping."""
        # Call parent mapping setup
        super()._setup_mapping()

        # group samples by type
        self._samples_by_type = {}
        for sample in self._samples:
            sample_type = sample.sample_type
            if sample_type not in self._samples_by_type:
                self._samples_by_type[sample_type] = []
            self._samples_by_type[sample_type].append(sample)

        return
    
    def _setup_graph(self):
        
        graph = self._get_project_graph()
        
        # assign parent/child relationship
        for edge in graph.get("edges", []):
            
            parent_id = edge["source"]
            child_id  = edge["target"]
            
            parent = self.get_sample(parent_id)
            child  = self.get_sample(child_id)
            
            if parent is not None and child is not None:
                child.add_parent(parent)
            else:
                logger.warn("Graph info inconsistent")
        
        # build graph with networkx
        self._graph = build_project_graph(self.samples)
                
        return

    @property
    def datasets(self):
        return self._datasets
    
    @property
    def graph(self):
        return self._graph

    def get_samples_by_type(self, sample_type):
        """
        Get all samples of a specific type.

        Parameters
        ----------
        sample_type : str
            The sample type to filter by (e.g., "thin film", "solution", etc.)

        Returns
        -------
        list
            List of Sample objects matching the specified type
        """
        return self._samples_by_type.get(sample_type, [])

    def get_samples_collection(self, sample_type):
        """
        Get a Samples collection for a specific sample type.

        Creates a Samples instance containing all samples of the specified type,
        enabling use of measurement loading methods (get_uvvis_data, get_well_images, etc.).

        Parameters
        ----------
        sample_type : str
            The sample type to filter by (e.g., "thin film", "solution", etc.)

        Returns
        -------
        Samples
            A Samples collection instance containing samples of the specified type

        Examples
        --------
        >>> project = CrucibleProject(project_id="10k_perovskites")
        >>> thin_films = project.get_samples_collection("thin film")
        >>> thin_films.get_uvvis_data()
        """
        from tksamples import Samples

        samples_list = self.get_samples_by_type(sample_type)
        return Samples(samples=samples_list, from_crucible=False,
                      cache_dir=self._cache_dir, use_cache=self._use_cache,
                      overwrite_cache=self._overwrite_cache,
                      project_id=self.project_id, sample_type=sample_type)

    @property
    def sample_types(self):
        """Get list of all unique sample types in the project."""
        return list(self._samples_by_type.keys())

    # Graph-based genealogy queries

    def get_ancestors(self, sample):
        """
        Get all ancestor samples using the project graph.

        Uses networkx to efficiently find all ancestors in the genealogy graph.

        Parameters
        ----------
        sample : Sample or str
            Sample object or sample unique_id/name

        Returns
        -------
        list of Sample
            List of all ancestor Sample objects

        Examples
        --------
        >>> project = CrucibleProject("10k_perovskites")
        >>> sample = project["TF0001"]
        >>> ancestors = project.get_ancestors(sample)
        """
        # Get Sample object if string was passed
        if isinstance(sample, str):
            sample = self.get_sample(sample_id=sample, sample_name=sample)
            if sample is None:
                logger.warning(f"Sample '{sample}' not found")
                return []

        if sample not in self._graph:
            logger.debug(f"Sample {sample.sample_name} not in genealogy graph")
            return []

        ancestor_samples = nx.ancestors(self._graph, sample)
        return list(ancestor_samples)

    def get_descendants(self, sample):
        """
        Get all descendant samples using the project graph.

        Uses networkx to efficiently find all descendants in the genealogy graph.

        Parameters
        ----------
        sample : Sample or str
            Sample object or sample unique_id/name

        Returns
        -------
        list of Sample
            List of all descendant Sample objects

        Examples
        --------
        >>> project = CrucibleProject("10k_perovskites")
        >>> solution = project["SOL0001"]
        >>> descendants = project.get_descendants(solution)
        """
        # Get Sample object if string was passed
        if isinstance(sample, str):
            sample = self.get_sample(sample_id=sample, sample_name=sample)
            if sample is None:
                logger.warning(f"Sample '{sample}' not found")
                return []

        if sample not in self._graph:
            logger.debug(f"Sample {sample.sample_name} not in genealogy graph")
            return []

        descendant_samples = nx.descendants(self._graph, sample)
        return list(descendant_samples)

    def get_common_ancestors(self, sample1, sample2):
        """
        Find common ancestors of two samples.

        Parameters
        ----------
        sample1 : Sample or str
            First sample object or unique_id/name
        sample2 : Sample or str
            Second sample object or unique_id/name

        Returns
        -------
        list of Sample
            List of Sample objects that are ancestors of both samples

        Examples
        --------
        >>> project = CrucibleProject("10k_perovskites")
        >>> tf1 = project["TF0001"]
        >>> tf2 = project["TF0002"]
        >>> common = project.get_common_ancestors(tf1, tf2)
        """
        # Get Sample objects if strings were passed
        if isinstance(sample1, str):
            sample1 = self.get_sample(sample_id=sample1, sample_name=sample1)
            if sample1 is None:
                logger.warning(f"Sample '{sample1}' not found")
                return []

        if isinstance(sample2, str):
            sample2 = self.get_sample(sample_id=sample2, sample_name=sample2)
            if sample2 is None:
                logger.warning(f"Sample '{sample2}' not found")
                return []

        if sample1 not in self._graph or sample2 not in self._graph:
            logger.debug(f"One or both samples not in genealogy graph")
            return []

        ancestors1 = nx.ancestors(self._graph, sample1)
        ancestors2 = nx.ancestors(self._graph, sample2)
        common_samples = ancestors1.intersection(ancestors2)

        return list(common_samples)

    def get_siblings(self, sample):
        """
        Get sibling samples (samples sharing at least one parent).

        Parameters
        ----------
        sample : Sample or str
            Sample object or unique_id/name

        Returns
        -------
        list of Sample
            List of sibling Sample objects

        Examples
        --------
        >>> project = CrucibleProject("10k_perovskites")
        >>> sample = project["TF0001"]
        >>> siblings = project.get_siblings(sample)
        """
        # Get Sample object if string was passed
        if isinstance(sample, str):
            sample = self.get_sample(sample_id=sample, sample_name=sample)
            if sample is None:
                logger.warning(f"Sample '{sample}' not found")
                return []

        if sample not in self._graph:
            logger.debug(f"Sample {sample.sample_name} not in genealogy graph")
            return []

        # Get all parents
        parents = list(self._graph.predecessors(sample))

        # Get all children of those parents
        siblings = set()
        for parent in parents:
            siblings.update(self._graph.successors(parent))

        # Remove the sample itself
        siblings.discard(sample)

        return list(siblings)

    def get_samples_with_ancestor(self, ancestor):
        """
        Get all samples that have the specified sample as an ancestor.

        This is equivalent to getting all descendants.

        Parameters
        ----------
        ancestor : Sample or str
            Ancestor sample object or unique_id

        Returns
        -------
        list of Sample
            List of all samples descended from the ancestor

        Examples
        --------
        >>> project = CrucibleProject("10k_perovskites")
        >>> solution = project["SOL0001"]
        >>> all_from_solution = project.get_samples_with_ancestor(solution)
        """
        return self.get_descendants(ancestor)
    
    def __repr__(self):
        """Return string representation of the collection."""
        return f"{self.__class__.__name__}({self.project_id} | {self.nsamples} samples)"