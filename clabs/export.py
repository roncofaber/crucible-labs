#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export selected measurements into one folder per sample.

Nano owns file transfer; this module decides whether cached files are valid,
groups samples sharing a dataset so each downloads once, and writes outputs
that survive interruption and can be resumed.
"""

import glob
import hashlib
import logging
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional

from crucible.utils.io import storage_display_name

from clabs.utils.auxiliary import atomic_path

logger = logging.getLogger(__name__)


class DatasetFileError(RuntimeError):
    """A dataset's files could not be obtained in a valid state."""


@dataclass
class LocalFile:
    path: Path
    name: str
    size: Optional[int]
    sha256: Optional[str]


@dataclass
class MeasurementExport:
    """How to export one kind of measurement.

    ``selection`` maps sample name to its chosen dataset. ``writer(dataset,
    files, targets)`` writes every ``{sample: path}`` target and returns a
    ``{sample: record}`` mapping. ``filename(sample, files)`` names the output.
    ``describe(path)`` rebuilds a record for an output skipped on resume.
    ``is_current(path, dataset, files)``, if given, says whether an existing
    output still comes from the selected source; if not, it is rewritten.
    With ``multiple=True``, each sample maps to a list of datasets,
    ``filename(sample, files, dataset)`` names each output, and records are
    lists carrying each record's ``dataset_mfid``.
    """
    name: str
    selection: Mapping
    writer: Callable
    filename: Callable
    describe: Callable
    is_current: Optional[Callable] = None
    multiple: bool = False


@dataclass
class ExportResult:
    records: dict = field(default_factory=dict)
    failures: list = field(default_factory=list)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_valid(local, check_hash=True):
    if not local.path.is_file():
        return False
    if local.size is not None and local.path.stat().st_size != local.size:
        return False
    return not check_hash or local.sha256 is None or sha256_file(local.path) == local.sha256


def ensure_dataset_files(client, mfid, cache_dir, check_hash=True):
    """Return a dataset's files from the cache, downloading any missing or invalid ones.

    ``check_hash=False`` validates by size only, which is much faster for
    repeated loading of a large cache.
    """
    groups = {}
    for record in client.datasets.list_files(mfid):
        name = storage_display_name(record, mfid)
        if not name:
            continue
        if os.path.isabs(name):
            name = os.path.basename(name)
        local = LocalFile(Path(cache_dir) / mfid / name, name,
                          record.get("size"), record.get("sha256_hash"))
        groups.setdefault(record.get("storage_path") or name, []).append(local)

    def _resolved(group):
        """A stored object has one true record; the others are stale leftovers."""
        return next((f for f in group if _is_valid(f, check_hash)), None)

    stale = [f for group in groups.values() if _resolved(group) is None for f in group]
    if stale:
        client.datasets.download(
            mfid,
            output_dir=str(cache_dir),
            no_record=True,
            overwrite_existing=True,
            include=[glob.escape(f.name) for f in stale],
        )

    files = []
    for group in groups.values():
        match = _resolved(group)
        if match is None:
            raise DatasetFileError(f"Dataset {mfid}: invalid after download: {[f.name for f in group]}")
        if len(group) > 1:
            logger.warning(f"Dataset {mfid}: {len(group)} file records share one stored object; "
                           f"using {match.name}")
        files.append(match)
    return files


def copy_file_writer(dataset, files, targets):
    """Copy a dataset's single file to every target, verifying each copy."""
    if len(files) != 1:
        raise DatasetFileError(
            f"Dataset {dataset.unique_id}: expected one file, found {[f.name for f in files]}")
    source = files[0]
    expected = source.sha256 or sha256_file(source.path)
    records = {}
    for sample, target in targets.items():
        with atomic_path(target) as tmp:
            shutil.copyfile(source.path, tmp)
            if sha256_file(tmp) != expected:
                raise DatasetFileError(f"Copy of {source.path} does not match its hash")
        records[sample] = {"path": str(target)}
    return records


def _group_by_dataset(selection, multiple):
    groups = {}
    for sample, chosen in selection.items():
        for dataset in (chosen if multiple else [chosen]):
            groups.setdefault(dataset.unique_id, (dataset, []))[1].append(sample)
    return groups


def _permissive(path, mode):
    umask = os.umask(0)
    os.umask(umask)
    os.chmod(path, mode & ~umask)


def folder_is_current(path, dataset, files):
    """True if ``path`` holds exactly the dataset's files, each with matching content."""
    path = Path(path)
    if not path.is_dir():
        return False
    present = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    if present != {f.name for f in files}:
        return False
    return all(_is_valid(LocalFile(path / f.name, f.name, f.size, f.sha256)) for f in files)


def copy_folder_writer(dataset, files, targets):
    """Copy all of a dataset's files into each target folder, verifying each copy.

    A folder is assembled under a temporary name and moved into place whole.
    """
    records = {}
    for sample, target in targets.items():
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"))
        try:
            _permissive(tmp, 0o777)
            for f in files:
                copy = tmp / f.name
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f.path, copy)
                _permissive(copy, 0o666)
                if not _is_valid(LocalFile(copy, f.name, f.size, f.sha256)):
                    raise DatasetFileError(f"Copy of {f.path} does not match its record")
            if target.exists():
                shutil.rmtree(target)
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)
        records[sample] = {"path": str(target)}
    return records


def _existing_record(export, path, dataset, files):
    """The record of a usable existing output, or ``None`` if it must be written."""
    if not path.exists():
        return None
    try:
        if export.is_current is not None and not export.is_current(path, dataset, files):
            logger.warning(f"{path}: not from the selected source, rewriting")
            return None
        return export.describe(path)
    except Exception as error:
        logger.warning(f"{path}: unreadable ({error}), rewriting")
        return None


def export_samples(client, out_dir, cache_dir, exports, workers=8, overwrite=False):
    """Write each export's selected measurements to ``out_dir/<sample>/``.

    A dataset that fails is recorded in ``failures`` with its samples, and the
    run continues. Existing outputs are skipped unless ``overwrite`` is true.

    Returns
    -------
    ExportResult
    """
    out_dir = Path(out_dir)
    result = ExportResult()
    for export in exports:
        groups = _group_by_dataset(export.selection, export.multiple)

        def _store(sample, record, dataset):
            key = (sample, export.name)
            if export.multiple:
                result.records.setdefault(key, []).append({**record, "dataset_mfid": dataset.unique_id})
            else:
                result.records[key] = record

        def _fail(dataset, samples, error):
            logger.error(f"{export.name}: {dataset.name!r} failed: {error}")
            result.failures.append({
                "export": export.name, "dataset_mfid": dataset.unique_id,
                "dataset_name": dataset.name, "films": sorted(samples), "error": str(error),
            })

        fetched = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(ensure_dataset_files, client, mfid, cache_dir): mfid
                       for mfid in groups}
            for future in as_completed(futures):
                mfid = futures[future]
                try:
                    fetched[mfid] = future.result()
                except Exception as error:
                    _fail(*groups[mfid], error)

        for mfid, (dataset, samples) in groups.items():
            if mfid not in fetched:
                continue
            files = fetched[mfid]
            targets = {}
            try:
                for sample in samples:
                    name = (export.filename(sample, files, dataset) if export.multiple
                            else export.filename(sample, files))
                    path = out_dir / sample / name
                    record = None if overwrite else _existing_record(export, path, dataset, files)
                    if record is None:
                        targets[sample] = path
                    else:
                        _store(sample, record, dataset)
                if not targets:
                    continue
                records = export.writer(dataset, files, targets)
            except Exception as error:
                _fail(dataset, list(targets) or samples, error)
                continue
            for sample in targets:
                if sample in records:
                    _store(sample, records[sample], dataset)
            absent = [sample for sample in targets if sample not in records]
            if absent:
                _fail(dataset, absent, "writer produced no output")
    return result
