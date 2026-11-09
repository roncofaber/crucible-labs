import itertools

from clabs import Dataset, Sample

_ids = itertools.count()


def _next_id(prefix):
    return f"{prefix}{next(_ids):08d}"


def make_sample(name, sample_type="thin film", sm=None, mfid=None):
    return Sample({
        "unique_id": mfid or _next_id("smp"),
        "sample_name": name,
        "sample_type": sample_type,
        "project_id": "test",
        "scientific_metadata": sm,
    })


def make_dataset(name, measurement, session=None, sm=None, timestamp=None, mfid=None):
    return Dataset({
        "unique_id": mfid or _next_id("dst"),
        "dataset_name": name,
        "measurement": measurement,
        "session_name": session,
        "project_id": "test",
        "scientific_metadata": sm,
        "timestamp": timestamp,
    })
